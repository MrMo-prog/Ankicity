// Anki-City Frontend Controller - 2D Side Scrolling
let state = {
    resources: { straw: 999, wood: 999, stone: 999, gold: 999 },
    current_counter: 24,
    cards_per_resource: 24,
    next_resource: 'straw',
    street_lineup: [],
    unlocked_cosmetics: ['default'],
    streak: 0,
    costs: {}
};

// Metadata for building upgrade descriptions
const BUILDINGS_METADATA = {
    HOUSE: {
        name: "House",
        effects: {
            1: "Provides basic housing. (+5 population)",
            2: "Improves comfort. (+15 population)",
            3: "Spacious stone design. (+50 population)",
            4: "Grand manor style. (+120 population)"
        }
    },
    TOWNHALL: {
        name: "Town Hall",
        effects: {
            1: "Resources awarded every 20 reviews.",
            2: "Speeds up reviews to 19 per resource.",
            3: "Speeds up reviews to 17 per resource.",
            4: "Speeds up reviews to 15 per resource."
        }
    },
    TAVERN: {
        name: "Tavern",
        effects: {
            1: "Unlocks Tavern menu. Trades Straw ➡️ Wood.",
            2: "Unlocks trading Wood ➡️ Stone.",
            3: "Unlocks trading Stone ➡️ Gold.",
            4: "Adds grand common room. (+50 population)"
        }
    },
    STRAW_MILL: {
        name: "Straw Mill",
        effects: {
            1: "Grants +5% chance of double Straw.",
            2: "Grants +12% chance of double Straw.",
            3: "Grants +25% chance of double Straw.",
            4: "Grants +40% chance of double Straw."
        }
    },
    SAWMILL: {
        name: "Sawmill",
        effects: {
            1: "Grants +5% chance of double Wood.",
            2: "Grants +12% chance of double Wood.",
            3: "Grants +25% chance of double Wood.",
            4: "Grants +40% chance of double Wood."
        }
    },
    QUARRY: {
        name: "Quarry",
        effects: {
            1: "Grants +5% chance of double Stone.",
            2: "Grants +12% chance of double Stone.",
            3: "Grants +25% chance of double Stone.",
            4: "Grants +40% chance of double Stone."
        }
    },
    GOLD_MINE: {
        name: "Gold Mine",
        effects: {
            1: "Grants +5% chance of double Gold.",
            2: "Grants +12% chance of double Gold.",
            3: "Grants +25% chance of double Gold.",
            4: "Grants +40% chance of double Gold, and increases Gold drop rate to 10%."
        }
    }
};

// Initial setup when JS loads
document.addEventListener('DOMContentLoaded', () => {
    // Notify Python backend we are ready to fetch state
    if (typeof pycmd !== 'undefined') {
        pycmd("ankicity:ready");
    } else {
        // Fallback for browser-based sandbox testing
        // Mocking the backend for isolated testing
        state.street_lineup = [
            {id: "HOUSE", tier: 1},
            {id: "HOUSE", tier: 1},
            {id: "SAWMILL", tier: 1},
            {id: "HOUSE", tier: 1},
            {id: "TAVERN", tier: 1},
            {id: "HOUSE", tier: 1},
            {id: "HOUSE", tier: 1},
            {id: "TOWNHALL", tier: 1},
            {id: "HOUSE", tier: 1},
            {id: "HOUSE", tier: 1},
            {id: "STRAW_MILL", tier: 1},
            {id: "QUARRY", tier: 1},
            {id: "HOUSE", tier: 1},
            {id: "HOUSE", tier: 1},
            {id: "GOLD_MINE", tier: 1}
        ];
        state.costs = {
            "HOUSE_lvl2": { straw: 10, wood: 5 },
            "TOWNHALL_lvl2": { wood: 15, stone: 5 }
        };
        renderApp();
    }
});

// Standard Anki listener registered globally
window.onAnkiData = function(command, data) {
    if (command === "state_update") {
        state = data;
        renderApp();
    } else if (command === "error") {
        showToast(data.message, true);
    } else if (command === "toast") {
        showToast(data.message, false);
    }
};

// Communicate actions to Python with local fallback for sandbox mode
function triggerAction(actionName, payload = {}) {
    if (typeof pycmd !== 'undefined') {
        pycmd(`ankicity:${actionName}:${JSON.stringify(payload)}`);
    } else {
        console.log(`Action: ${actionName}`, payload);
        handleLocalActionFallback(actionName, payload);
    }
}

// Sandbox local simulation handler
function handleLocalActionFallback(action, payload) {
    if (action === "upgrade") {
        const { index } = payload;
        const cell = state.street_lineup[index];
        if (cell && cell.tier < 4) {
            const next_tier = cell.tier + 1;
            const cost_key = `${cell.id}_lvl${next_tier}`;
            const cost = state.costs[cost_key] || {};
            for (const [res, amt] of Object.entries(cost)) {
                state.resources[res] = Math.max(0, (state.resources[res] || 0) - amt);
            }
            cell.tier = next_tier;
            recalculateLocalEfficiency();
            checkLocalMilestones();
            renderApp();
        }
    } else if (action === "trade") {
        const { from_res, to_res } = payload;
        if (state.resources[from_res] >= 3) {
            state.resources[from_res] -= 3;
            state.resources[to_res] = (state.resources[to_res] || 0) + 1;
            renderApp();
            showToast(`Traded 3x ${from_res} for 1x ${to_res}!`, false);
        }
    } else if (action === "claim_milestone") {
        const { threshold } = payload;
        state.pending_milestones = (state.pending_milestones || []).filter(m => m.threshold !== threshold);
        renderApp();
    } else if (action === "hide_dashboard") {
        state.dashboard_visible = false;
        renderApp();
    } else if (action === "restore_dashboard") {
        state.dashboard_visible = true;
        renderApp();
    }
}

function checkLocalMilestones() {
    const pop = getPopulation();
    const lastMilestone = state.last_milestone_claimed || 0;
    if (!state.pending_milestones) state.pending_milestones = [];
    
    let currentThreshold = 100;
    while (currentThreshold <= pop) {
        if (currentThreshold > lastMilestone) {
            const rewards = { straw: 0, wood: 0, stone: 0, gold: 0 };
            for (let i = 0; i < 5; i++) {
                const r = Math.random();
                if (r < 0.45) rewards.straw++;
                else if (r < 0.80) rewards.wood++;
                else if (r < 0.95) rewards.stone++;
                else rewards.gold++;
            }
            for (const [res, count] of Object.entries(rewards)) {
                state.resources[res] = (state.resources[res] || 0) + count;
            }
            state.pending_milestones.push({
                threshold: currentThreshold,
                rewards: rewards
            });
            state.last_milestone_claimed = currentThreshold;
        }
        currentThreshold += 100;
    }
}

function recalculateLocalEfficiency() {
    let town_hall_tier = 1;
    state.street_lineup.forEach(cell => {
        if (cell.id === "TOWNHALL") {
            town_hall_tier = cell.tier;
        }
    });
    const repsMap = {1: 20, 2: 19, 3: 17, 4: 15};
    state.cards_per_resource = repsMap[town_hall_tier] || 20;
}

// Calculate total population based on street buildings
function getPopulation() {
    let pop = 0;
    state.street_lineup.forEach(cell => {
        if (cell.id === "HOUSE") {
            if (cell.tier === 1) pop += 5;
            else if (cell.tier === 2) pop += 15;
            else if (cell.tier === 3) pop += 50;
            else if (cell.tier === 4) pop += 120;
        } else if (cell.id === "TOWNHALL") {
            if (cell.tier === 1) pop += 10;
            else if (cell.tier === 2) pop += 30;
            else if (cell.tier === 3) pop += 100;
            else if (cell.tier === 4) pop += 250;
        }
    });
    return pop;
}

// Render the application
function renderApp() {
    const app = document.getElementById('app');
    app.innerHTML = '';

    if (state.dashboard_visible === false) {
        const minimized = document.createElement('div');
        minimized.className = 'minimized-bar';
        minimized.innerHTML = `
            <span class="minimized-text">🌆 Anki-City is hidden</span>
            <button class="hud-btn" id="hud-btn-restore" title="Open City View (Ctrl+Alt+C)">➕ Show City</button>
        `;
        app.appendChild(minimized);
        minimized.querySelector('#hud-btn-restore').addEventListener('click', () => {
            triggerAction("restore_dashboard");
        });
        return;
    }

    // Create HUD
    const hud = document.createElement('div');
    hud.className = 'hud';
    
    // Check if Anki is in night mode to match styling
    if (document.body.classList.contains('nightMode')) {
        hud.classList.add('night');
    }

    const pop = getPopulation();
    const nextMilestonePop = (Math.floor(pop / 100) + 1) * 100;
    const progress = Math.max(0, Math.min(100, ((state.cards_per_resource - state.current_counter) / state.cards_per_resource) * 100));

    const nextEmojiMap = { straw: '🌾', wood: '🪵', stone: '🪨', gold: '🪙' };
    const nextLabel = nextEmojiMap[state.next_resource] || state.next_resource;

    hud.innerHTML = `
        <div class="hud-resources">
            <div class="resource-item" title="Straw (Common)">🌾 <span>${state.resources.straw}</span></div>
            <div class="resource-item" title="Wood (Common)">🪵 <span>${state.resources.wood}</span></div>
            <div class="resource-item" title="Stone (Rare)">🪨 <span>${state.resources.stone}</span></div>
            <div class="resource-item" title="Gold (Epic)">🪙 <span>${state.resources.gold}</span></div>
            <div class="population-container">
                <div class="resource-item" title="Total Population">👥 <span>${pop}</span></div>
                <div class="milestone-forecast">Next Milestone Reward (at Pop ${nextMilestonePop}): 5x Resources</div>
            </div>
        </div>
        <div class="hud-center">
            <span>Next: <b>${nextLabel}</b> (${state.current_counter} left)</span>
            <div class="progress-container">
                <div class="progress-bar" style="width: ${progress}%"></div>
            </div>
            <span title="Consecutive learning streak">🔥 <b>${state.streak}</b>d</span>
        </div>
        <div class="hud-actions">
            <button class="hud-btn" id="hud-btn-tavern" title="Trade resources">🍻 Tavern</button>
            <button class="hud-btn" id="hud-btn-hide" title="Hide City Dashboard (Ctrl+Alt+C)">➖ Hide</button>
        </div>
    `;
    app.appendChild(hud);

    // Programmatically bind events for HUD buttons (fixes CSP issues)
    hud.querySelector('#hud-btn-tavern').addEventListener('click', openTavernModal);
    hud.querySelector('#hud-btn-hide').addEventListener('click', () => {
        triggerAction("hide_dashboard");
    });

    // Create Viewport
    const viewport = document.createElement('div');
    viewport.className = 'city-viewport';
    
    // Render 2D Street
    const lineup = state.street_lineup || [];
    lineup.forEach((cell, index) => {
        const slot = document.createElement('div');
        slot.className = 'street-slot';
        slot.dataset.index = index;
        
        const b = document.createElement('img');
        b.className = `building-sprite type-${cell.id} level-${cell.tier}`;
        b.src = `images/${cell.id}_lvl${cell.tier}.png`;
        b.alt = `${cell.id} Level ${cell.tier}`;
        slot.appendChild(b);
        
        // Vertical spacer to sit precisely on the sand riverbank path
        const spacer = document.createElement('div');
        spacer.className = 'street-slot-spacer';
        slot.appendChild(spacer);
        
        // Capsule badge at the bottom
        const badgeName = cell.id.replace('_', ' ');
        const badge = document.createElement('div');
        badge.className = 'building-badge';
        badge.innerText = `${badgeName} Lvl ${cell.tier}`;
        slot.appendChild(badge);
        
        // Inline popover in the sky
        const popover = createInlinePopover(index, cell);
        slot.appendChild(popover);
        
        slot.addEventListener('click', (e) => {
            // Prevent toggling if click is inside popover itself
            if (e.target.closest('.building-popover')) {
                return;
            }
            togglePopover(slot);
        });
        
        viewport.appendChild(slot);
    });
    
    app.appendChild(viewport);

    // Create Resize Handle at the top of the widget
    const resizeHandle = document.createElement('div');
    resizeHandle.className = 'resize-handle';
    app.prepend(resizeHandle);
    setupResizeHandler(resizeHandle);
    
    // Automatically scroll to the Townhall in the middle
    setTimeout(() => {
        viewport.scrollLeft = (viewport.scrollWidth - viewport.clientWidth) / 2;
    }, 50);

    // Check for pending milestones and display them
    if (state.pending_milestones && state.pending_milestones.length > 0) {
        if (!document.querySelector('.modal-overlay.active')) {
            showMilestoneModal(state.pending_milestones[0]);
        }
    }
}

// Drag-to-resize widget logic
let isResizing = false;
let startY = 0;
let startHeight = 0;
let currentHeight = 0;

function setupResizeHandler(handle) {
    handle.addEventListener('mousedown', (e) => {
        isResizing = true;
        startY = e.clientY;
        startHeight = window.innerHeight;
        currentHeight = startHeight;
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        e.preventDefault();
    });
}

function handleMouseMove(e) {
    if (!isResizing) return;
    const dy = e.clientY - startY;
    currentHeight = Math.max(150, Math.min(800, startHeight - dy)); // Dragging down makes it smaller
    triggerAction("resize", { height: currentHeight });
}

function handleMouseUp(e) {
    if (isResizing) {
        isResizing = false;
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        triggerAction("resize_end", { height: currentHeight });
    }
}


// Create inline sky popover
function createInlinePopover(index, cell) {
    const popover = document.createElement('div');
    popover.className = 'building-popover';
    
    const meta = BUILDINGS_METADATA[cell.id] || { name: cell.id.replace('_', ' '), effects: {} };
    
    const title = document.createElement('div');
    title.className = 'popover-title';
    title.innerText = meta.name;
    popover.appendChild(title);
    
    const subtitle = document.createElement('div');
    subtitle.className = 'popover-subtitle';
    subtitle.innerText = `Current Level: ${cell.tier} / 4`;
    popover.appendChild(subtitle);
    
    // Add effect descriptions
    const desc = document.createElement('div');
    desc.style.fontSize = '11px';
    desc.style.margin = '4px 0 8px 0';
    desc.style.lineHeight = '1.3';
    
    const currentEff = meta.effects[cell.tier] || "Basic building.";
    let descHtml = `<div style="opacity: 0.85;"><b>Current:</b> ${currentEff}</div>`;
    
    if (cell.tier < 4) {
        const nextEff = meta.effects[cell.tier + 1];
        descHtml += `<div style="margin-top: 4px; color: #3182ce; font-weight: 500;"><b>Next Level:</b> ${nextEff}</div>`;
    }
    desc.innerHTML = descHtml;
    popover.appendChild(desc);
    
    const costs = state.costs || {};
    
    if (cell.tier < 4) {
        const nextTier = cell.tier + 1;
        const cost_key = `${cell.id}_lvl${nextTier}`;
        const cost = costs[cost_key] || {};
        
        const costContainer = document.createElement('div');
        costContainer.className = 'popover-cost-container';
        
        let canUpgrade = true;
        const emojiMap = { straw: '🌾', wood: '🪵', stone: '🪨', gold: '🪙' };
        
        const costItems = Object.entries(cost);
        if (costItems.length === 0) {
            costContainer.innerHTML = '<span class="popover-cost-badge">Free</span>';
        } else {
            costItems.forEach(([res, amt]) => {
                const has = state.resources[res] || 0;
                const isInsufficient = has < amt;
                if (isInsufficient) canUpgrade = false;
                
                const badge = document.createElement('span');
                badge.className = `popover-cost-badge ${isInsufficient ? 'insufficient' : ''}`;
                badge.innerHTML = `${emojiMap[res]} ${amt}`;
                costContainer.appendChild(badge);
            });
        }
        popover.appendChild(costContainer);
        
        const upgradeBtn = document.createElement('button');
        upgradeBtn.className = 'popover-btn';
        upgradeBtn.innerText = `Upgrade to Tier ${nextTier}`;
        if (!canUpgrade) {
            upgradeBtn.disabled = true;
        } else {
            upgradeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                upgradeBuilding(index);
            });
        }
        popover.appendChild(upgradeBtn);
    } else {
        const maxText = document.createElement('div');
        maxText.style.fontSize = '11px';
        maxText.style.fontWeight = 'bold';
        maxText.style.color = '#48bb78';
        maxText.style.margin = '10px 0';
        maxText.innerText = '✨ Maximum level reached! ✨';
        popover.appendChild(maxText);
    }
    
    return popover;
}

// Toggle Popover Active states
function togglePopover(slot) {
    const popover = slot.querySelector('.building-popover');
    const wasActive = popover.classList.contains('active');
    
    // Close other popovers first
    document.querySelectorAll('.building-popover').forEach(p => {
        p.classList.remove('active');
    });
    document.querySelectorAll('.street-slot').forEach(s => {
        s.classList.remove('selected');
    });
    
    if (!wasActive) {
        popover.classList.add('active');
        slot.classList.add('selected');
    }
}

// Close popovers on click outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.street-slot')) {
        document.querySelectorAll('.building-popover').forEach(p => {
            p.classList.remove('active');
        });
        document.querySelectorAll('.street-slot').forEach(s => {
            s.classList.remove('selected');
        });
    }
});

// Tavern Modal (Marketplace Trading)
function openTavernModal() {
    const tavernCell = state.street_lineup.find(c => c.id === "TAVERN");
    
    const overlay = createOverlay();
    overlay.querySelector('.modal-title').innerText = "Tavern & Trade Hub";

    if (!tavernCell) {
        const emptyDiv = document.createElement('div');
        emptyDiv.style.textAlign = 'center';
        emptyDiv.style.padding = '12px';
        emptyDiv.style.opacity = '0.8';
        emptyDiv.innerHTML = `
            🍻 <b>The Tavern is missing!</b><br><br>
            A Tavern must be present in your street lineup.
        `;
        overlay.querySelector('.modal-body').appendChild(emptyDiv);
    } else {
        const tavernTier = tavernCell.tier;
        const canTradeStraw = state.resources.straw >= 3;
        const canTradeWood = state.resources.wood >= 3;
        const canTradeStone = state.resources.stone >= 3;

        const tradeBox = document.createElement('div');
        tradeBox.className = 'trade-box';
        
        const ratioHeader = document.createElement('div');
        ratioHeader.style.fontSize = '12px';
        ratioHeader.style.fontWeight = 'bold';
        ratioHeader.style.textAlign = 'center';
        ratioHeader.style.marginBottom = '8px';
        ratioHeader.style.opacity = '0.9';
        ratioHeader.innerText = "Trade Ratio: 3:1";
        tradeBox.appendChild(ratioHeader);
        
        const trades = [
            { from: 'straw', to: 'wood', label: '🌾 3x Straw ➡️ 🪵 1x Wood', canTrade: canTradeStraw, reqTier: 1 },
            { from: 'wood', to: 'stone', label: '🪵 3x Wood ➡️ 🪨 1x Stone', canTrade: canTradeWood, reqTier: 2 },
            { from: 'stone', to: 'gold', label: '🪨 3x Stone ➡️ 🪙 1x Gold', canTrade: canTradeStone, reqTier: 3 }
        ];
        
        trades.forEach(t => {
            const row = document.createElement('div');
            row.className = 'trade-row';
            
            const isLocked = tavernTier < t.reqTier;
            row.innerHTML = `<span>${t.label}</span>`;
            
            const btn = document.createElement('button');
            btn.className = 'trade-btn';
            
            if (isLocked) {
                btn.innerText = `Lvl ${t.reqTier} 🔒`;
                btn.disabled = true;
                btn.title = `Requires Tavern Level ${t.reqTier} to unlock.`;
                row.style.opacity = '0.5';
            } else {
                btn.innerText = 'Trade';
                if (!t.canTrade) {
                    btn.disabled = true;
                } else {
                    btn.addEventListener('click', () => {
                        tradeResource(t.from, t.to);
                        closeOverlay();
                    });
                }
            }
            row.appendChild(btn);
            tradeBox.appendChild(row);
        });
        overlay.querySelector('.modal-body').appendChild(tradeBox);
    }
    activateOverlay(overlay);
}

// Helper methods to execute actions
function upgradeBuilding(index) {
    triggerAction("upgrade", { index });
}

function tradeResource(from_res, to_res) {
    triggerAction("trade", { from_res, to_res });
}

// Overlay DOM creation utility
function createOverlay() {
    closeOverlay();

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
        <div class="modal">
            <div class="modal-header">
                <span class="modal-title">Menu</span>
                <span class="modal-close" id="modal-close-btn">✕</span>
            </div>
            <div class="modal-body"></div>
        </div>
    `;
    
    overlay.querySelector('#modal-close-btn').addEventListener('click', closeOverlay);
    document.body.appendChild(overlay);
    return overlay;
}

function activateOverlay(overlay) {
    setTimeout(() => {
        overlay.classList.add('active');
    }, 10);
}

function closeOverlay() {
    const overlays = document.querySelectorAll('.modal-overlay');
    overlays.forEach(o => {
        o.classList.remove('active');
        setTimeout(() => o.remove(), 200);
    });
}

// Toast Notifications
function showToast(message, isError = false) {
    let toast = document.getElementById('ankicity-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'ankicity-toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    
    toast.innerText = message;
    toast.style.borderColor = isError ? 'rgba(245, 101, 101, 0.4)' : 'rgba(255, 255, 255, 0.1)';
    toast.style.color = isError ? '#feb2b2' : 'white';
    
    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 2500);
}

function showMilestoneModal(milestone) {
    const overlay = createOverlay();
    overlay.querySelector('.modal-title').innerText = "🎉 Milestone Reward!";
    
    // Hide close button so they must claim it
    overlay.querySelector('#modal-close-btn').style.display = 'none';

    const modalBody = overlay.querySelector('.modal-body');
    modalBody.innerHTML = '';

    const content = document.createElement('div');
    content.style.textAlign = 'center';
    content.style.padding = '8px 0';
    
    const subtitle = document.createElement('div');
    subtitle.style.fontSize = '14px';
    subtitle.style.fontWeight = 'bold';
    subtitle.style.marginBottom = '16px';
    subtitle.innerText = `City population reached ${milestone.threshold}!`;
    content.appendChild(subtitle);

    const desc = document.createElement('div');
    desc.style.fontSize = '12px';
    desc.style.marginBottom = '16px';
    desc.innerText = "You have been awarded 5 random resources:";
    content.appendChild(desc);

    const rewardGrid = document.createElement('div');
    rewardGrid.style.display = 'flex';
    rewardGrid.style.justifyContent = 'center';
    rewardGrid.style.gap = '12px';
    rewardGrid.style.marginBottom = '20px';

    const emojiMap = { straw: '🌾', wood: '🪵', stone: '🪨', gold: '🪙' };
    const nameMap = { straw: 'Straw', wood: 'Wood', stone: 'Stone', gold: 'Gold' };

    for (const [res, count] of Object.entries(milestone.rewards)) {
        if (count > 0) {
            const card = document.createElement('div');
            card.className = 'reward-card';

            const icon = document.createElement('span');
            icon.style.fontSize = '24px';
            icon.innerText = emojiMap[res] || '📦';
            card.appendChild(icon);

            const amountText = document.createElement('span');
            amountText.style.fontWeight = 'bold';
            amountText.style.fontSize = '16px';
            amountText.style.marginTop = '4px';
            amountText.innerText = `+${count}`;
            card.appendChild(amountText);

            const nameText = document.createElement('span');
            nameText.style.fontSize = '10px';
            nameText.style.opacity = '0.75';
            nameText.innerText = nameMap[res] || res;
            card.appendChild(nameText);

            rewardGrid.appendChild(card);
        }
    }
    content.appendChild(rewardGrid);

    const claimBtn = document.createElement('button');
    claimBtn.className = 'popover-btn';
    claimBtn.style.padding = '10px';
    claimBtn.style.fontSize = '14px';
    claimBtn.innerText = "Claim Rewards 🎁";
    claimBtn.addEventListener('click', () => {
        triggerAction("claim_milestone", { threshold: milestone.threshold });
        closeOverlay();
    });
    content.appendChild(claimBtn);

    modalBody.appendChild(content);
    activateOverlay(overlay);
}
