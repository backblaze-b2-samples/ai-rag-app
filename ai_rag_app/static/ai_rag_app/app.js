function rearrangePage() {
  document.getElementById("history").classList.remove("d-none");
  document.getElementById("prompt-row").classList.remove("h-100");
  document.getElementById("prompt-col").classList.remove("align-self-center");
  document.getElementById("ask-me-header").remove();
  document.getElementById("new-chat").classList.remove("d-none");
}

function historyScrollToBottom() {
  const history = document.getElementById("history");
  history.scrollTop = history.scrollHeight;
}

function appendText(text, type, elapsed) {
  const newDiv = document.createElement('div');
  newDiv.classList.add(type);
  const textParagraph = document.createElement('p');
  textParagraph.innerHTML = text;
  newDiv.appendChild(textParagraph);
  if (type === "ai") {
    const timePara = document.createElement('p');
    timePara.classList.add('time');
    timePara.textContent = elapsed.toFixed(1) + " seconds";
    newDiv.appendChild(timePara);
  }
  document.getElementById("conversation").appendChild(newDiv);
  return textParagraph;
}

function startDots() {
  const NBSP = "\u00A0";  // non-breaking space
  const para = appendText(NBSP, "dots");
  let counter = 0
  return [setInterval(() => {
    para.textContent = ". ".repeat(counter);
    if (para.textContent.length === 0) {
      // Need to have content in the paragraph, otherwise the conversation history scrolls up and down!
      para.textContent = NBSP;
    }
    counter = (counter + 1) % 4;
  }, 350), para];
}

function stopDots([intervalID, para]) {
  clearInterval(intervalID);
  para.remove();
}

function showAnswer(text, elapsed, dots, prompt) {
  stopDots(dots);
  appendText(text, "ai", elapsed);
  historyScrollToBottom();
  prompt.value = "";
  prompt.disabled = false;
  document.getElementById("new-chat").disabled = false;
}

function submitOnEnter(event) {
  if (event.which === 13) {
    if (!event.repeat) {
      if (document.getElementById("conversation").getElementsByTagName("div").length === 0) {
        // If we're in the initial "no messages" state, rearrange the
        // page to show the conversation and move the prompt to the bottom
        rearrangePage();
      }
      const question = event.target.value;
      if (question.trim().length > 0) {
        event.target.value = "Please wait...";
        event.target.disabled = true;
        document.getElementById("new-chat").disabled = true;
        appendText(question, "human");
        const dots = startDots();
        historyScrollToBottom();
        fetch("api/ask_question", {
          method: "POST",
          body: JSON.stringify({"question": question}),
          headers: {"Content-Type": "application/json"}
        })
            .then((response) => response.json())
            .then((data) => {
              showAnswer(data["answer"], data["elapsed"], dots, event.target);
            })
            .catch((error) => {
              console.error(error);
              showAnswer(error, 0, dots, event.target);
            })
      }
    }
    event.preventDefault();
  }
}

function newChat() {
  const urlParams = new URLSearchParams(window.location.search);
  urlParams.set('newchat', '1')
  window.location.href = '?' + urlParams.toString()
}

function removeNewChat() {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('newchat')) {
    urlParams.delete('newchat')
    const url = urlParams.size > 0 ? '?' + urlParams.toString() : window.location.pathname;
    window.history.pushState({}, '', url)
  }
}

document.getElementById("question").addEventListener("keydown", submitOnEnter);
document.getElementById("new-chat").addEventListener("click", newChat);

window.addEventListener("load", function() {
  historyScrollToBottom();
  removeNewChat();
});
