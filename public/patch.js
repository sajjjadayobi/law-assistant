// ==================== Law Agent UI Enhancements ====================

// ==================== ClipboardItem Polyfill ====================
// Some browsers expose navigator.clipboard.write but not ClipboardItem.
// Chainlit uses both together; when ClipboardItem is undefined it throws a
// ReferenceError. Force Chainlit's fallback path (writeText) in that case.
if (typeof ClipboardItem === 'undefined' && navigator.clipboard) {
    navigator.clipboard.write = undefined;
}

// ==================== Input Placeholder ====================

function changeInputPlaceholder() {
    const inputField = document.querySelector('textarea[placeholder*="message"]') ||
                      document.querySelector('textarea');

    if (inputField) {
        inputField.placeholder = "سوال خودتون رو اینجا بنویسید";
        inputField.setAttribute('dir', 'rtl');
        inputField.style.textAlign = 'right';
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', changeInputPlaceholder);
} else {
    changeInputPlaceholder();
}

setTimeout(changeInputPlaceholder, 500);
setTimeout(changeInputPlaceholder, 1000);

// ==================== Auto Direction Detection for Messages ====================
// CSS `direction: auto` only checks the first strongly-typed character.
// This function counts Persian vs Latin characters for a more reliable decision.

function detectPersianRatio(text) {
    const persian = (text.match(/[؀-ۿ]/g) || []).length;
    const latin = (text.match(/[a-zA-Z]/g) || []).length;
    const total = persian + latin;
    return total === 0 ? 0 : persian / total;
}

function applyAutoDirection() {
    document.querySelectorAll('.prose, [class*="message-content"]').forEach(el => {
        // Skip code elements
        if (el.closest('pre') || el.closest('code')) return;
        // Skip already-processed elements
        if (el.dataset.autoDir) return;

        const text = el.innerText || el.textContent || '';
        if (text.trim().length < 5) return;

        const ratio = detectPersianRatio(text);

        if (ratio > 0.3) {
            el.setAttribute('dir', 'rtl');
        } else if (ratio < 0.1 && text.trim().length > 20) {
            el.setAttribute('dir', 'ltr');
        }
        // Mixed content: leave direction to CSS `direction: auto`

        el.dataset.autoDir = '1';
    });
}

// ==================== Copy to Clipboard for Code Blocks ====================

function copyToClipboardFallback(text) {
    try {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        const success = document.execCommand('copy');
        document.body.removeChild(textArea);
        return success;
    } catch (err) {
        return false;
    }
}

function addCopyButtons() {
    document.querySelectorAll('pre').forEach(pre => {
        if (pre.querySelector('.copy-btn')) return;

        const btn = document.createElement('button');
        btn.className = 'copy-btn';
        btn.textContent = 'کپی';
        btn.title = 'کپی کد';

        btn.addEventListener('click', () => {
            try {
                const code = pre.querySelector('code');
                const text = code ? code.innerText : pre.innerText;

                if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
                    navigator.clipboard.writeText(text)
                        .then(() => {
                            btn.textContent = '✓ کپی شد';
                            setTimeout(() => { btn.textContent = 'کپی'; }, 2000);
                        })
                        .catch(() => {
                            if (copyToClipboardFallback(text)) {
                                btn.textContent = '✓ کپی شد';
                                setTimeout(() => { btn.textContent = 'کپی'; }, 2000);
                            } else {
                                btn.textContent = 'خطا';
                                setTimeout(() => { btn.textContent = 'کپی'; }, 2000);
                            }
                        });
                } else {
                    if (copyToClipboardFallback(text)) {
                        btn.textContent = '✓ کپی شد';
                        setTimeout(() => { btn.textContent = 'کپی'; }, 2000);
                    } else {
                        btn.textContent = 'خطا';
                        setTimeout(() => { btn.textContent = 'کپی'; }, 2000);
                    }
                }
            } catch (error) {
                btn.textContent = 'خطا';
                setTimeout(() => { btn.textContent = 'کپی'; }, 2000);
            }
        });

        pre.appendChild(btn);
    });
}

// ==================== Single MutationObserver for All DOM Updates ====================

const domObserver = new MutationObserver(() => {
    changeInputPlaceholder();
    addCopyButtons();
    applyAutoDirection();
});

domObserver.observe(document.body, { childList: true, subtree: true });

// Run immediately and after React hydration delays
addCopyButtons();
applyAutoDirection();
setTimeout(() => { addCopyButtons(); applyAutoDirection(); }, 500);
setTimeout(() => { addCopyButtons(); applyAutoDirection(); }, 1500);
