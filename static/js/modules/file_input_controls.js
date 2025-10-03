const FILE_INPUT_SELECTOR = 'input[type="file"][name$="media_file"], input[type="file"][name$="image"]';

function createClearButton(fileInput) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'file-input-clear-btn';
    button.setAttribute('aria-label', 'Remove selected file');
    button.textContent = '×';

    button.addEventListener('click', (event) => {
        event.preventDefault();
        clearFileInput(fileInput);
    });

    return button;
}

function clearFileInput(fileInput) {
    try {
        fileInput.value = '';

        if (typeof DataTransfer === 'function' && fileInput.files && fileInput.files.length) {
            const dataTransfer = new DataTransfer();
            fileInput.files = dataTransfer.files;
        }
    } catch (error) {
        fileInput.value = '';
    }

    const changeEvent = new Event('change', { bubbles: true });
    fileInput.dispatchEvent(changeEvent);
}

function updateButtonVisibility(fileInput, button) {
    const hasValue = Boolean(fileInput.value || (fileInput.files && fileInput.files.length));
    button.style.display = hasValue ? 'inline-flex' : 'none';
}

function attachClearButton(fileInput) {
    if (!fileInput || fileInput.dataset.clearButtonAttached === 'true') {
        return;
    }

    const button = createClearButton(fileInput);

    fileInput.insertAdjacentElement('afterend', button);

    const syncVisibility = () => updateButtonVisibility(fileInput, button);
    fileInput.addEventListener('change', syncVisibility);
    fileInput.addEventListener('input', syncVisibility);

    // Initial state
    syncVisibility();

    fileInput.dataset.clearButtonAttached = 'true';
}

export function initFileInputControls(root = document) {
    const scope = root instanceof HTMLElement ? root : document;
    const fileInputs = scope.querySelectorAll(FILE_INPUT_SELECTOR);
    fileInputs.forEach(attachClearButton);
}

export function attachClearButtonToInput(fileInput) {
    attachClearButton(fileInput);
}
