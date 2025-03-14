/**
 * MIT License
 *
 * Copyright (c) 2025 Backblaze, Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

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
              showAnswer("I'm afraid I can't do that, Dave - there was a problem submitting your question. " +
                  "If you're technically inclined, look in the JavaScript console for more detail.",
                  0, dots, event.target);
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

// Trim spurious newlines and any other whitespace from copied data
function copyListener(event) {
  const range = window.getSelection().getRangeAt(0),
      rangeContents = range.cloneContents();

  // rangeContents.innerText and innerHTML are undefined, so we need to put it in a div
  const divElement = document.createElement('div')
  divElement.appendChild(rangeContents);

  event.clipboardData.setData("text/plain", divElement.innerText.trim());
  event.clipboardData.setData("text/html", divElement.innerHTML);
  divElement.remove()
  event.preventDefault();
}

document.getElementById("question").addEventListener("keydown", submitOnEnter);
document.getElementById("new-chat").addEventListener("click", newChat);

window.addEventListener("load", function() {
  historyScrollToBottom();
  removeNewChat();
  document.getElementById("question").focus();
});

document.addEventListener("copy", copyListener);
