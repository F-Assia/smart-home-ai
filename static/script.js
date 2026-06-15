const temperatureEl = document.getElementById("temperature");
const lightStatusEl = document.getElementById("lightStatus");
const fanSpeedEl = document.getElementById("fanSpeed");
const predictionEl = document.getElementById("prediction");
const lightToggle = document.getElementById("lightToggle");
const fanSlider = document.getElementById("fanSlider");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const chatLog = document.getElementById("chatLog");

let latestState = { temperature: 0, light: false, fan: 0, history: [] };

const chart = new Chart(document.getElementById("temperatureChart"), {
    type: "line",
    data: {
        labels: [],
        datasets: [{
            label: "Temperature \u00B0C",
            data: [],
            borderColor: "#2364d2",
            backgroundColor: "rgba(35, 100, 210, 0.12)",
            borderWidth: 3,
            pointRadius: 3,
            tension: 0.35,
            fill: true,
        }],
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
        },
        scales: {
            x: {
                grid: { display: false },
            },
            y: {
                beginAtZero: false,
                ticks: {
                    callback: (value) => `${value} \u00B0C`,
                },
            },
        },
    },
});

function addMessage(text, type = "system") {
    const item = document.createElement("div");
    item.className = `message ${type}`;
    item.textContent = text;
    chatLog.appendChild(item);
    chatLog.scrollTop = chatLog.scrollHeight;
}

function formatTime(timestamp) {
    if (!timestamp) return "";
    return new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function renderState(data) {
    latestState = data;
    temperatureEl.textContent = Number(data.temperature || 0).toFixed(1);
    lightStatusEl.textContent = data.light ? "ON" : "OFF";
    fanSpeedEl.textContent = data.fan || 0;
    predictionEl.textContent = Number(data.predicted_temperature || 0).toFixed(1);
    fanSlider.value = data.fan || 0;
    lightToggle.textContent = data.light ? "Turn off" : "Turn on";

    const history = data.history || [];
    chart.data.labels = history.map((sample) => formatTime(sample.timestamp));
    chart.data.datasets[0].data = history.map((sample) => sample.temperature);
    chart.update("none");
}

async function fetchState() {
    try {
        const response = await fetch("/api/state");
        if (!response.ok) throw new Error("State request failed");
        renderState(await response.json());
    } catch (error) {
        addMessage("Unable to refresh dashboard state.", "error");
    }
}

async function postJson(url, payload) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.error || "Request failed");
    }
    renderState(data.state);
    return data;
}

lightToggle.addEventListener("click", async () => {
    try {
        await postJson("/api/light", { light: !latestState.light });
    } catch (error) {
        addMessage(error.message, "error");
    }
});

fanSlider.addEventListener("change", async (event) => {
    try {
        await postJson("/api/fan", { fan: Number(event.target.value) });
    } catch (error) {
        addMessage(error.message, "error");
    }
});

chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = chatInput.value.trim();
    if (!message) return;

    addMessage(message, "user");
    chatInput.value = "";

    try {
        const data = await postJson("/api/ask", { message });
        const action = data.action;
        if (action.action === "none") {
            addMessage("No device action was detected.");
        } else {
            addMessage(`Executed ${action.action}: ${action.value} (${data.source}).`);
        }
    } catch (error) {
        addMessage(error.message, "error");
    }
});

addMessage("Try: turn on the light, or set fan to 75 percent.");
fetchState();
setInterval(fetchState, 2000);
