// ==================== Law Agent UI Enhancements ====================
// Changes input placeholder to Persian with RTL direction

function changeInputPlaceholder() {
    const inputField = document.querySelector('textarea[placeholder*="message"]') ||
                      document.querySelector('textarea');

    if (inputField) {
        inputField.placeholder = "سوال خودتون رو اینجا بنویسید";
        inputField.setAttribute('dir', 'rtl');
        inputField.style.textAlign = 'right';
    }
}

// Run on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', changeInputPlaceholder);
} else {
    changeInputPlaceholder();
}

// Watch for placeholder changes and reapply
const observer = new MutationObserver(() => {
    changeInputPlaceholder();
});

observer.observe(document.body, {
    childList: true,
    subtree: true
});

// Also try immediately and after a delay
setTimeout(changeInputPlaceholder, 500);
setTimeout(changeInputPlaceholder, 1000);

// ==================== Copy to Clipboard for Code Blocks ====================

function addCopyButtons() {
    document.querySelectorAll('pre').forEach(pre => {
        if (pre.querySelector('.copy-btn')) return;

        const btn = document.createElement('button');
        btn.className = 'copy-btn';
        btn.textContent = 'کپی';
        btn.title = 'کپی کد';

        btn.addEventListener('click', () => {
            const code = pre.querySelector('code');
            const text = code ? code.innerText : pre.innerText;
            navigator.clipboard.writeText(text).then(() => {
                btn.textContent = '✓ کپی شد';
                setTimeout(() => { btn.textContent = 'کپی'; }, 2000);
            }).catch(() => {
                btn.textContent = 'خطا';
                setTimeout(() => { btn.textContent = 'کپی'; }, 2000);
            });
        });

        pre.appendChild(btn);
    });
}

const copyObserver = new MutationObserver(addCopyButtons);
copyObserver.observe(document.body, { childList: true, subtree: true });
addCopyButtons();
