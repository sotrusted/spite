const CLIPBOARD_TARGET_SELECTOR = 'textarea[name="content"], textarea#id_content';
const FILE_INPUT_SELECTOR = 'input[type="file"][name$="media_file"], input[type="file"][name$="image"]';
const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024;

const activeTimers = new WeakMap();

function attachPasteListener(textarea) {
    if (!textarea || textarea.dataset.clipboardHandlerAttached === 'true') {
        return;
    }

    textarea.addEventListener('paste', (event) => handlePaste(event, textarea));
    textarea.dataset.clipboardHandlerAttached = 'true';
}

function handlePaste(event, textarea) {
    const clipboardData = event.clipboardData || window.clipboardData;
    if (!clipboardData) {
        return;
    }

    const file = extractImageFile(clipboardData);
    if (!file) {
        return;
    }

    const form = textarea.closest('form');
    if (!form) {
        return;
    }

    const fileInput = form.querySelector(FILE_INPUT_SELECTOR);
    if (!fileInput) {
        return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
        showFeedback(fileInput, 'Clipboard image is larger than 50 MB and was not attached.');
        return;
    }

    const preparedFile = normalizeFile(file);
    const hadExistingFile = fileInput.files && fileInput.files.length > 0;

    const filesAssigned = assignFileToInput(fileInput, preparedFile, clipboardData);
    if (!filesAssigned) {
        showFeedback(fileInput, 'Clipboard image could not be attached in this browser.');
        return;
    }

    // Prevent the default paste (typically inserts empty string) so cursor stays unchanged
    event.preventDefault();

    triggerChange(fileInput);

    const statusMessage = hadExistingFile
        ? `Replaced existing upload with clipboard image (${formatBytes(preparedFile.size)}).`
        : `Attached clipboard image (${formatBytes(preparedFile.size)}).`;

    showFeedback(fileInput, statusMessage);
}

function extractImageFile(clipboardData) {
    if (clipboardData.items) {
        for (const item of clipboardData.items) {
            if (item.kind === 'file' && item.type.startsWith('image/')) {
                const file = item.getAsFile();
                if (file) {
                    return file;
                }
            }
        }
    }

    if (clipboardData.files && clipboardData.files.length > 0) {
        // Safari exposes clipboard images via files without items support
        const file = clipboardData.files[0];
        if (file && file.type && file.type.startsWith('image/')) {
            return file;
        }
    }

    return null;
}

function normalizeFile(file) {
    const extension = inferExtension(file.type) || 'png';
    const baseName = file.name && file.name !== 'image.png' ? file.name : `clipboard-image-${Date.now()}.${extension}`;

    try {
        return new File([file], baseName, { type: file.type, lastModified: Date.now() });
    } catch (error) {
        return file;
    }
}

function inferExtension(mimeType) {
    if (!mimeType) {
        return null;
    }

    const parts = mimeType.split('/');
    return parts.length === 2 ? parts[1] : null;
}

function assignFileToInput(fileInput, file, clipboardData) {
    if (typeof DataTransfer === 'function') {
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        fileInput.files = dataTransfer.files;
        return true;
    }

    if (clipboardData && clipboardData.files && clipboardData.files.length) {
        try {
            fileInput.files = clipboardData.files;
            return true;
        } catch (error) {
            // Continue to fallback where possible
        }
    }

    if (fileInput.files && 'length' in fileInput.files && fileInput.files.length === 0) {
        try {
            fileInput.files = createFileList(file);
            return true;
        } catch (error) {
            return false;
        }
    }

    return false;
}

function createFileList(file) {
    let dataTransfer = null;

    if (typeof ClipboardEvent === 'function') {
        try {
            const clipboardEvent = new ClipboardEvent('');
            if (clipboardEvent.clipboardData) {
                dataTransfer = clipboardEvent.clipboardData;
            }
        } catch (error) {
            dataTransfer = null;
        }
    }

    if (!dataTransfer) {
        throw new Error('Clipboard API unavailable');
    }

    dataTransfer.items.add(file);
    return dataTransfer.files;
}

function triggerChange(input) {
    const changeEvent = new Event('change', { bubbles: true });
    input.dispatchEvent(changeEvent);
}

function formatBytes(bytes) {
    if (!Number.isFinite(bytes)) {
        return 'unknown size';
    }

    const units = ['bytes', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex += 1;
    }

    const precision = unitIndex === 0 ? 0 : 1;
    return `${size.toFixed(precision)} ${units[unitIndex]}`;
}

function showFeedback(fileInput, message) {
    const container = fileInput.closest('.form-group, .form-row, .control-group') || fileInput.parentElement;
    if (!container) {
        return;
    }

    let feedback = container.querySelector('.clipboard-upload-hint');
    if (!feedback) {
        feedback = document.createElement('div');
        feedback.className = 'clipboard-upload-hint';
        container.appendChild(feedback);
    }

    feedback.textContent = message;
    feedback.style.display = 'block';

    const activeTimer = activeTimers.get(feedback);
    if (activeTimer) {
        clearTimeout(activeTimer);
    }

    const timer = window.setTimeout(() => {
        feedback.style.display = 'none';
    }, 5000);
    activeTimers.set(feedback, timer);
}

export function initClipboardMediaSupport(root = document) {
    const scope = root instanceof HTMLElement ? root : document;
    const textareas = scope.querySelectorAll(CLIPBOARD_TARGET_SELECTOR);
    textareas.forEach(attachPasteListener);
}

export function attachClipboardListenerToElement(element) {
    if (element && element.matches(CLIPBOARD_TARGET_SELECTOR)) {
        attachPasteListener(element);
    }
}
