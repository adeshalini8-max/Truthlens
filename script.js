/*
    TRUTHLENS
    Simple Rule-Based Fact Checker
*/


// ==============================
// VERIFIED CLAIM DATABASE
// ==============================

const verifiedClaims = [

    {
        keywords: [
            "earth revolves around the sun",
            "earth goes around the sun"
        ],

        verdict: "SUPPORTED",

        category: "Science",

        explanation:
            "The Earth orbits the Sun. This is an established scientific fact.",

        source:
            "NASA"
    },


    {
        keywords: [
            "sun revolves around the earth",
            "sun goes around the earth"
        ],

        verdict: "FALSE",

        category: "Science",

        explanation:
            "The Earth orbits the Sun. The apparent movement of the Sun across the sky is caused by Earth's rotation.",

        source:
            "NASA"
    },


    {
        keywords: [
            "taj mahal is in mumbai",
            "taj mahal located in mumbai"
        ],

        verdict: "FALSE",

        category: "History / Geography",

        explanation:
            "The Taj Mahal is located in Agra, Uttar Pradesh, India.",

        source:
            "Archaeological Survey of India"
    },


    {
        keywords: [
            "water freezes at 0 c",
            "water freezes at 0°c"
        ],

        verdict: "SUPPORTED",

        category: "Science",

        explanation:
            "Pure water freezes at 0°C under standard atmospheric pressure.",

        source:
            "National Institute of Standards and Technology"
    }

];



// ==============================
// TEXT / IMAGE TABS
// ==============================

function showTextChecker() {

    document.getElementById("textChecker")
        .classList.remove("hidden");

    document.getElementById("imageChecker")
        .classList.add("hidden");


    const tabs = document.querySelectorAll(".tab");

    tabs[0].classList.add("active");

    tabs[1].classList.remove("active");
}



function showImageChecker() {

    document.getElementById("textChecker")
        .classList.add("hidden");

    document.getElementById("imageChecker")
        .classList.remove("hidden");


    const tabs = document.querySelectorAll(".tab");

    tabs[0].classList.remove("active");

    tabs[1].classList.add("active");
}



// ==============================
// CHARACTER COUNTER
// ==============================

const claimInput =
    document.getElementById("claim");


claimInput.addEventListener(
    "input",
    function () {

        document.getElementById("charCount")
            .textContent = this.value.length;

    }
);



// ==============================
// CHECK CLAIM
// ==============================

function checkClaim() {

    const userClaim =
        document.getElementById("claim")
            .value
            .trim()
            .toLowerCase();


    if (userClaim === "") {

        alert("Please enter a claim first.");

        return;
    }


    let matchedClaim = null;


    for (const item of verifiedClaims) {

        for (const keyword of item.keywords) {

            if (userClaim.includes(keyword)) {

                matchedClaim = item;

                break;

            }

        }


        if (matchedClaim) {

            break;

        }

    }



    if (matchedClaim) {

        displayResult(
            matchedClaim.verdict,
            document.getElementById("claim").value,
            matchedClaim.explanation,
            matchedClaim.category,
            matchedClaim.source
        );

    }

    else {

        displayResult(

            "UNVERIFIED",

            document.getElementById("claim").value,

            "This claim is not currently available in the TruthLens verified database. This does not mean the claim is false. More evidence is required to verify it.",

            "Not Available",

            "No verified source found"

        );

    }

}



// ==============================
// DISPLAY RESULT
// ==============================

function displayResult(
    verdict,
    claim,
    explanation,
    category,
    source
) {

    const resultSection =
        document.getElementById("resultSection");


    const verdictElement =
        document.getElementById("verdict");


    verdictElement.textContent =
        getVerdictIcon(verdict) + " " + verdict;


    verdictElement.className =
        "verdict " + verdict.toLowerCase();


    document.getElementById("resultClaim")
        .textContent = claim;


    document.getElementById("resultExplanation")
        .textContent = explanation;


    document.getElementById("resultCategory")
        .textContent = category;


    document.getElementById("resultSource")
        .textContent = source;


    resultSection.classList.remove("hidden");


    resultSection.scrollIntoView({
        behavior: "smooth"
    });

}



// ==============================
// VERDICT ICON
// ==============================

function getVerdictIcon(verdict) {

    if (verdict === "SUPPORTED") {

        return "🟢";

    }


    if (verdict === "FALSE") {

        return "🔴";

    }


    if (verdict === "MISLEADING") {

        return "🟡";

    }


    return "⚪";

}



// ==============================
// IMAGE PREVIEW
// ==============================

function previewImage(event) {

    const file =
        event.target.files[0];


    if (!file) {

        return;

    }


    const reader =
        new FileReader();


    reader.onload = function(e) {

        document.getElementById("imagePreview")
            .src = e.target.result;


        document.getElementById(
            "imagePreviewContainer"
        ).classList.remove("hidden");

    };


    reader.readAsDataURL(file);

}



// ==============================
// IMAGE CHECK
// ==============================

function checkImage() {

    alert(
        "Image upload is working. Automatic image fact-checking will be added in the next version."
    );

}