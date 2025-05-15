document.addEventListener("DOMContentLoaded", () => {
    const postContentTextarea = document.getElementById("postContent");
    const platformTabs = document.querySelectorAll(".platform-tab");
    const previewPlatforms = {
        twitter: document.getElementById("previewTwitter"),
        facebook: document.getElementById("previewFacebook"),
        linkedin: document.getElementById("previewLinkedIn")
    };
    const postContentAreas = {
        twitter: document.getElementById("twitterPostContent"),
        facebook: document.getElementById("facebookPostContent"),
        linkedin: document.getElementById("linkedinPostContent")
    };
    const getScoreBtn = document.getElementById("getScoreBtn");
    const scoreArea = document.getElementById("scoreArea");
    const scoreValue = document.getElementById("scoreValue");
    const scoreFeedback = document.getElementById("scoreFeedback");

    let currentPlatform = "twitter"; // Default platform

    function updateAllPreviews(content) {
        for (const platform in postContentAreas) {
            if (postContentAreas[platform]) {
                postContentAreas[platform].textContent = content || "Your post will appear here...";
            }
        }
    }

    function switchPlatformView(platform) {
        currentPlatform = platform;
        platformTabs.forEach(tab => {
            tab.classList.remove("border-blue-500", "text-blue-500", "font-semibold");
            tab.classList.add("text-gray-500", "hover:text-blue-500");
            if (tab.dataset.platform === platform) {
                tab.classList.add("border-blue-500", "text-blue-500", "font-semibold");
                tab.classList.remove("text-gray-500", "hover:text-blue-500");
            }
        });

        for (const key in previewPlatforms) {
            if (previewPlatforms[key]) {
                previewPlatforms[key].classList.add("hidden");
            }
        }
        if (previewPlatforms[platform]) {
            previewPlatforms[platform].classList.remove("hidden");
        }
    }

    if (postContentTextarea) {
        postContentTextarea.addEventListener("input", (e) => {
            updateAllPreviews(e.target.value);
        });
    }

    platformTabs.forEach(tab => {
        tab.addEventListener("click", () => {
            switchPlatformView(tab.dataset.platform);
        });
    });

    if (getScoreBtn) {
        getScoreBtn.addEventListener("click", async () => {
            const postText = postContentTextarea.value.trim();
            if (!postText) {
                alert("Please enter some post content before getting a score.");
                return;
            }

            scoreArea.classList.remove("hidden");
            scoreValue.textContent = "--/100";
            scoreFeedback.textContent = "Analyzing... please wait.";
            getScoreBtn.disabled = true;
            getScoreBtn.classList.add("opacity-50", "cursor-not-allowed");

            try {
                const response = await fetch("/api/score_post", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ 
                        post_text: postText,
                        platform: currentPlatform
                    }),
                });

                const result = await response.json();

                if (response.ok) {
                    scoreValue.textContent = `${result.score}/100`;
                    scoreFeedback.textContent = result.feedback;
                } else {
                    scoreValue.textContent = "Error";
                    scoreFeedback.textContent = result.error || "Failed to get score. Please try again.";
                }
            } catch (error) {
                console.error("Error fetching score:", error);
                scoreValue.textContent = "Error";
                scoreFeedback.textContent = "An error occurred while contacting the scoring service.";
            } finally {
                getScoreBtn.disabled = false;
                getScoreBtn.classList.remove("opacity-50", "cursor-not-allowed");
            }
        });
    }

    switchPlatformView(currentPlatform);
    updateAllPreviews("");
});
