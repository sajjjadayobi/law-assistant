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
