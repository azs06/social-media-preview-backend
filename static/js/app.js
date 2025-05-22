document.addEventListener("DOMContentLoaded", () => {
  // Main content and platform elements
  const postContentTextarea = document.getElementById("postContent");
  const platformTabs = document.querySelectorAll(".platform-tab");

  // Image elements
  const postImageInput = document.getElementById("postImage");
  const removeImageBtn = document.getElementById("removeImageBtn");

  // Preview elements
  const previewPlatforms = {
    twitter: document.getElementById("previewTwitter"),
    facebook: document.getElementById("previewFacebook"),
    linkedin: document.getElementById("previewLinkedIn"),
  };
  const postContentAreas = {
    twitter: document.getElementById("twitterPostContent"),
    facebook: document.getElementById("facebookPostContent"),
    linkedin: document.getElementById("linkedinPostContent"),
  };
  // Image previews for each platform
  const platformImagePreviews = {
    twitter: document.getElementById("twitterImagePreview"),
    facebook: document.getElementById("facebookImagePreview"),
    linkedin: document.getElementById("linkedinImagePreview"),
  };

  // Score and feedback elements
  const getScoreBtn = document.getElementById("getScoreBtn");
  const scoreArea = document.getElementById("scoreArea");
  const scoreValue = document.getElementById("scoreValue");
  const scoreFeedback = document.getElementById("scoreFeedback");
  const suggestionsArea = document.getElementById("suggestionsArea");
  const scoreSuggestions = document.getElementById("scoreSuggestions");

  let currentPlatform = "facebook"; // Default platform
  let currentImageBase64 = null; // To store the base64 string of the image

  // --- Image Handling ---
  if (postImageInput) {
    postImageInput.addEventListener("change", function (event) {
      const file = event.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
          removeImageBtn.classList.remove("hidden");
          // Store base64 string without the data URL prefix
          currentImageBase64 = e.target.result.split(",")[1];
          updateAllImagePreviews(e.target.result);
        };
        reader.readAsDataURL(file);
      }
    });
  }

  if (removeImageBtn) {
    removeImageBtn.addEventListener("click", () => {
      postImageInput.value = ""; // Clear the file input
      removeImageBtn.classList.add("hidden");
      currentImageBase64 = null;
      updateAllImagePreviews(null); // Clear platform image previews
    });
  }

  function updateAllImagePreviews(src) {
    for (const platform in platformImagePreviews) {
      if (platformImagePreviews[platform]) {
        if (src) {
          platformImagePreviews[platform].src = src;
          platformImagePreviews[platform].classList.remove("hidden");
        } else {
          platformImagePreviews[platform].src = "#";
          platformImagePreviews[platform].classList.add("hidden");
        }
      }
    }
  }

  // --- Content and Platform Preview Logic ---
  function updateAllTextPreviews(content) {
    for (const platform in postContentAreas) {
      if (postContentAreas[platform]) {
        postContentAreas[platform].textContent =
          content || "Your post will appear here...";
      }
    }
  }

  function switchPlatformView(platform) {
    currentPlatform = platform;
    platformTabs.forEach((tab) => {
      tab.classList.remove(
        "active",
        "border-blue-500",
        "text-blue-500",
        "font-semibold",
      );
      tab.classList.add(
        "text-gray-500",
        "hover:text-blue-500",
        "border-transparent",
      );
      if (tab.dataset.platform === platform) {
        tab.classList.add(
          "active",
          "border-blue-500",
          "text-blue-500",
          "font-semibold",
        );
        tab.classList.remove(
          "text-gray-500",
          "hover:text-blue-500",
          "border-transparent",
        );
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
      updateAllTextPreviews(e.target.value);
    });
  }

  platformTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      switchPlatformView(tab.dataset.platform);
    });
  });

  // --- API Call and Score Display ---
  if (getScoreBtn) {
    getScoreBtn.addEventListener("click", async () => {
      const postText = postContentTextarea.value.trim();
      if (!postText) {
        // Using a more prominent way to show error, instead of alert.
        scoreArea.classList.remove("hidden");
        scoreValue.textContent = "N/A";
        scoreFeedback.textContent =
          "Post content cannot be empty. Please write something.";
        suggestionsArea.classList.add("hidden");
        scoreSuggestions.textContent = "";
        return;
      }

      scoreArea.classList.remove("hidden");
      scoreValue.textContent = "--/100";
      scoreFeedback.textContent = "Analyzing... please wait.";
      suggestionsArea.classList.add("hidden");
      scoreSuggestions.textContent = "";
      getScoreBtn.disabled = true;
      getScoreBtn.classList.add("opacity-50", "cursor-not-allowed");

      const requestBody = {
        post_text: postText,
        platform: currentPlatform,
      };

      if (currentImageBase64) {
        requestBody.image_base64 = currentImageBase64;
      }

      try {
        const response = await fetch("/api/score_post", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(requestBody),
        });

        const result = await response.json();

        if (response.ok) {
          scoreValue.textContent = `${result.score}/100`;
          scoreFeedback.textContent = result.feedback;
          if (
            result.content_suggestions &&
            result.content_suggestions.trim() !== ""
          ) {
            scoreSuggestions.textContent = result.content_suggestions;
            suggestionsArea.classList.remove("hidden");
          } else {
            suggestionsArea.classList.add("hidden");
          }
        } else {
          scoreValue.textContent = "Error";
          scoreFeedback.textContent =
            result.error || "Failed to get score. Please try again.";
          suggestionsArea.classList.add("hidden");
        }
      } catch (error) {
        console.error("Error fetching score:", error);
        scoreValue.textContent = "Error";
        scoreFeedback.textContent =
          "An error occurred while contacting the scoring service.";
        suggestionsArea.classList.add("hidden");
      } finally {
        getScoreBtn.disabled = false;
        getScoreBtn.classList.remove("opacity-50", "cursor-not-allowed");
      }
    });
  }

  // Initial setup
  switchPlatformView(currentPlatform);
  updateAllTextPreviews(postContentTextarea ? postContentTextarea.value : "");
  updateAllImagePreviews(null); // Ensure image previews are initially hidden
});
