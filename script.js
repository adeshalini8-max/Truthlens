document.addEventListener("DOMContentLoaded", function () {

    const tabs = document.querySelectorAll(".checker-tab");
    const claimInput = document.getElementById("claimInput");
    const uploadArea = document.getElementById("uploadArea");
    const fileInput = document.getElementById("fileInput");
    const chooseFile = document.getElementById("chooseFile");
    const fileName = document.getElementById("fileName");
    const uploadTitle = document.getElementById("uploadTitle");
    const uploadDescription = document.getElementById("uploadDescription");
    const checkerHint = document.getElementById("checkerHint");
    const checkButton = document.getElementById("checkButton");
    const resultSection = document.getElementById("resultSection");
    const submitClaimButton = document.getElementById("submitClaimButton");

    let currentType = "text";
    let selectedFile = null;

    tabs.forEach(function (tab) {
        tab.addEventListener("click", function () {
            tabs.forEach(function (item) {
                item.classList.remove("active");
            });
            tab.classList.add("active");
            currentType = tab.getAttribute("data-type");
            resetChecker();
            updateChecker();
        });
    });

    function updateChecker() {
        if (currentType === "text") {
            claimInput.classList.remove("hidden");
            uploadArea.classList.add("hidden");
            claimInput.placeholder = "Paste a claim, message, headline or URL you want to check...";
            checkerHint.textContent = "Check information before you share it.";
            checkButton.innerHTML = 'Check Claim <span>→</span>';
            return;
        }

        claimInput.classList.add("hidden");
        uploadArea.classList.remove("hidden");
        checkButton.innerHTML = 'Upload & Check <span>→</span>';
        checkerHint.textContent = "Upload the media you want to examine.";

        if (currentType === "image") {
            uploadTitle.textContent = "Upload an image";
            uploadDescription.textContent = "Upload a screenshot or image containing a claim.";
            fileInput.accept = "image/png,image/jpeg,image/webp";
        }
        if (currentType === "audio") {
            uploadTitle.textContent = "Upload audio";
            uploadDescription.textContent = "Upload an audio recording containing a claim.";
            fileInput.accept = "audio/*";
        }
        if (currentType === "video") {
            uploadTitle.textContent = "Upload video";
            uploadDescription.textContent = "Upload a video containing information you want to check.";
            fileInput.accept = "video/*";
        }
    }

    chooseFile.addEventListener("click", function () {
        fileInput.click();
    });

    fileInput.addEventListener("change", function () {
        if (!fileInput.files.length) return;
        selectedFile = fileInput.files[0];
        fileName.textContent = "Selected: " + selectedFile.name;
    });

    checkButton.addEventListener("click", function () {
        if (currentType === "text") checkText();
        else checkMedia();
    });

    async function checkText() {
        const claim = claimInput.value.trim();
        if (!claim) {
            alert("Please enter a claim, message or URL first.");
            return;
        }

        showLoading();

        try {
            const response = await fetch("http://127.0.0.1:8000/api/fact-check/text", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: claim })
            });

            if (!response.ok) throw new Error("Backend response failed");

            const data = await response.json();
            showBackendResult(data);
        } catch (error) {
            console.error("FACT CHECK ERROR:", error);
            showResult(claim);
        }
    }

    function checkMedia() {
        if (!selectedFile) {
            alert("Please choose a " + currentType + " file first.");
            return;
        }
        showLoading();
        setTimeout(function () {
            showMediaResult();
        }, 800);
    }

    function showLoading() {
        resultSection.classList.remove("hidden");
        resultSection.innerHTML = `
            <div class="container">
                <div class="result-card loading-card">
                    <div class="loading-spinner"></div>
                    <h2>Preparing your check...</h2>
                    <p>TruthLens will examine the claim against available evidence and sources.</p>
                </div>
            </div>
        `;
        resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    function showBackendResult(data) {
        const claim = data.claim || "";
        const verdict = data.verdict || "UNVERIFIED";
        const explanation = data.explanation || "No explanation is available.";
        const sources = Array.isArray(data.sources) ? data.sources : [];

        let sourcesHTML = "<p>No sources were returned.</p>";
        if (sources.length) {
            sourcesHTML = sources.slice(0, 5).map(function (source) {
                const title = escapeHTML(source.name || source.title || source.source || "Source");
                const url = source.url || "#";
                return `<p><a href="${escapeHTML(url)}" target="_blank" rel="noopener noreferrer">${title}</a></p>`;
            }).join("");
        }

        resultSection.classList.remove("hidden");
        resultSection.innerHTML = `
            <div class="container">
                <div class="result-card">
                    <div class="result-top">
                        <span class="result-label">TRUTHLENS ASSESSMENT</span>
                        <span class="demo-badge">LIVE BACKEND</span>
                    </div>
                    <div class="result-verdict">
                        <span>${escapeHTML(verdict)}</span>
                        <h2>${escapeHTML(verdict === "SUPPORTED" ? "Evidence supports this claim." : "This claim needs evidence and context.")}</h2>
                    </div>
                    <div class="claim-display">
                        <small>CLAIM</small>
                        <p>"${escapeHTML(claim)}"</p>
                    </div>
                    <div class="result-explanation">
                        <h3>What does this assessment mean?</h3>
                        <p>${escapeHTML(explanation)}</p>
                    </div>
                    <div class="result-columns">
                        <div>
                            <span>THE EVIDENCE</span>
                            <p>${data.database_match ? "A matching record was found in the TruthLens reference database." : "Live evidence was retrieved for further comparison."}</p>
                        </div>
                        <div>
                            <span>SOURCES</span>
                            ${sourcesHTML}
                        </div>
                    </div>
                    <div class="result-method">
                        <strong>How we reached this assessment</strong>
                        <p>Claim → Evidence → Comparison → Explanation</p>
                    </div>
                </div>
            </div>
        `;
        resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    function showResult(claim) {
        resultSection.classList.remove("hidden");
        resultSection.innerHTML = `
            <div class="container">
                <div class="result-card">
                    <div class="result-top">
                        <span class="result-label">TRUTHLENS ASSESSMENT</span>
                        <span class="demo-badge">BACKEND OFFLINE</span>
                    </div>
                    <div class="result-verdict">
                        <span>UNVERIFIED</span>
                        <h2>This claim needs evidence.</h2>
                    </div>
                    <div class="claim-display">
                        <small>CLAIM</small>
                        <p>"${escapeHTML(claim)}"</p>
                    </div>
                    <div class="result-explanation">
                        <h3>What does this mean?</h3>
                        <p>The TruthLens backend could not be reached. Start the FastAPI server and try again.</p>
                    </div>
                    <div class="result-method">
                        <strong>Checking process</strong>
                        <p>Claim → Evidence → Comparison → Explanation</p>
                    </div>
                </div>
            </div>
        `;
        resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    function showMediaResult() {
        resultSection.classList.remove("hidden");
        resultSection.innerHTML = `
            <div class="container">
                <div class="result-card">
                    <div class="result-top">
                        <span class="result-label">${currentType.toUpperCase()}</span>
                        <span class="demo-badge">RECEIVED</span>
                    </div>
                    <div class="result-verdict">
                        <span>RECEIVED</span>
                        <h2>Your ${escapeHTML(currentType)} is ready.</h2>
                    </div>
                    <div class="claim-display">
                        <small>FILE</small>
                        <p>${escapeHTML(selectedFile.name)}</p>
                    </div>
                    <div class="result-explanation">
                        <h3>What happens next?</h3>
                        <p>TruthLens will extract claims from this ${escapeHTML(currentType)}, find evidence, compare sources and present an assessment.</p>
                    </div>
                </div>
            </div>
        `;
        resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    submitClaimButton.addEventListener("click", function () {
        alert("Claim submission form will be added in the next phase.");
    });

    function resetChecker() {
        claimInput.value = "";
        fileInput.value = "";
        fileName.textContent = "";
        selectedFile = null;
        resultSection.classList.add("hidden");
    }

    function escapeHTML(text) {
        const element = document.createElement("div");
        element.textContent = text == null ? "" : String(text);
        return element.innerHTML;
    }

    async function loadLatestFactChecks() {
        const factGrid = document.getElementById("latestFactGrid");
        if (!factGrid) return;

        try {
            const response = await fetch("http://127.0.0.1:8000/api/fact-check/history");
            if (!response.ok) throw new Error("Backend response failed");
            const data = await response.json();
            const checks = data.checks || [];

            if (!checks.length) return;

            factGrid.innerHTML = "";
            checks.slice(0, 3).forEach(function (check, index) {
                const article = document.createElement("article");
                article.className = "fact-card";
                const verdict = check.verdict || "UNVERIFIED";
                const claim = check.claim || "Claim unavailable";
                const explanation = check.explanation || "No explanation is available.";
                const topic = check.topic || "FACT CHECK";
                const imageClass = "image-" + ((index % 3) + 1);

                article.innerHTML = `
                    <div class="fact-image ${imageClass}">${escapeHTML(verdict)}</div>
                    <div class="fact-content">
                        <span class="category">${escapeHTML(topic)}</span>
                        <h3>${escapeHTML(claim)}</h3>
                        <p>${escapeHTML(explanation)}</p>
                        <div class="fact-meta">
                            <span>TruthLens</span>
                            <span>${escapeHTML(verdict)}</span>
                        </div>
                    </div>
                `;
                factGrid.appendChild(article);
            });
        } catch (error) {
            console.error("LATEST FACT CHECK ERROR:", error);
        }
    }

    loadLatestFactChecks();

    const animatedElements = document.querySelectorAll(
        ".section-heading, .fact-card, .topic-card, .explainer-card, " +
        ".method-step, .submit-container, .about-grid"
    );

    animatedElements.forEach(function (element) {
        element.classList.add("reveal");
    });

    if ("IntersectionObserver" in window) {
        const revealObserver = new IntersectionObserver(function (entries, observer) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;
                entry.target.classList.add("revealed");
                observer.unobserve(entry.target);
            });
        }, { threshold: 0.12 });

        animatedElements.forEach(function (element) {
            revealObserver.observe(element);
        });
    } else {
        animatedElements.forEach(function (element) {
            element.classList.add("revealed");
        });
    }

    const navbar = document.querySelector(".navbar");
    window.addEventListener("scroll", function () {
        if (!navbar) return;
        if (window.scrollY > 20) navbar.classList.add("scrolled");
        else navbar.classList.remove("scrolled");
    });

    updateChecker();
});
