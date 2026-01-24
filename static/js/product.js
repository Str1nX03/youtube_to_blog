document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generate-btn');
    const urlInput = document.getElementById('youtube-url');
    const statusMsg = document.getElementById('status-message');
    const blogContent = document.getElementById('blog-content');
    const btnText = document.querySelector('.btn-text');
    const btnLoader = document.getElementById('btn-loader');
    const copyBtn = document.getElementById('copy-btn');

    let rawMarkdown = "";

    generateBtn.addEventListener('click', async () => {
        const url = urlInput.value.trim();
        if (!url) {
            statusMsg.textContent = "⚠ Please enter a URL first.";
            statusMsg.style.color = "#ef4444";
            return;
        }

        // UI Reset
        setLoading(true);
        statusMsg.textContent = "Agents activated...";
        statusMsg.style.color = "#94a3b8";
        blogContent.innerHTML = '<div class="placeholder-text">Agents are working...<br>This usually takes 30-60 seconds.</div>';

        try {
            const response = await fetch('/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });

            const data = await response.json();

            if (response.ok) {
                rawMarkdown = data.content;
                // Render Markdown using the 'marked' library included in HTML head
                blogContent.innerHTML = marked.parse(rawMarkdown);
                statusMsg.textContent = "✔ Blog generated successfully!";
                statusMsg.style.color = "#22c55e";
                copyBtn.disabled = false;
            } else {
                throw new Error(data.error || "Unknown error occurred");
            }

        } catch (error) {
            statusMsg.textContent = `✖ Error: ${error.message}`;
            statusMsg.style.color = "#ef4444";
            blogContent.innerHTML = `<div class="placeholder-text" style="color:#ef4444">Generation Failed.<br>${error.message}</div>`;
        } finally {
            setLoading(false);
        }
    });

    copyBtn.addEventListener('click', () => {
        if (!rawMarkdown) return;
        navigator.clipboard.writeText(rawMarkdown).then(() => {
            const originalText = copyBtn.innerText;
            copyBtn.innerText = "Copied!";
            setTimeout(() => copyBtn.innerText = originalText, 2000);
        });
    });

    function setLoading(isLoading) {
        if (isLoading) {
            generateBtn.disabled = true;
            btnText.style.display = 'none';
            btnLoader.style.display = 'block';
            urlInput.disabled = true;
        } else {
            generateBtn.disabled = false;
            btnText.style.display = 'block';
            btnLoader.style.display = 'none';
            urlInput.disabled = false;
        }
    }
});