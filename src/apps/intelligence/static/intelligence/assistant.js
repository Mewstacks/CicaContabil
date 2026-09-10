(() => {
  const form = document.querySelector('[data-assistant-composer]');
  const question = form?.querySelector('textarea[name="question"]');
  const attachmentInput = form?.querySelector('input[type="file"][name="attachments"]');
  const preview = document.getElementById('attachment-preview');
  const submitButton = form?.querySelector('button[type="submit"]');
  const submitLabel = form?.querySelector('[data-submit-label]');
  const status = document.getElementById('composer-status');
  let draftChanged = false;

  const markDraftChanged = () => { draftChanged = true; };

  const renderAttachments = () => {
    if (!preview || !attachmentInput) return;
    preview.replaceChildren();
    [...attachmentInput.files].forEach((file) => {
      const item = document.createElement('span');
      item.textContent = file.name;
      preview.append(item);
    });
    preview.hidden = attachmentInput.files.length === 0;
  };

  document.querySelectorAll('[data-prompt]').forEach((button) => {
    button.addEventListener('click', () => {
      if (!question) return;
      question.value = button.dataset.prompt || '';
      question.focus();
    });
  });

  attachmentInput?.addEventListener('change', renderAttachments);
  attachmentInput?.addEventListener('change', markDraftChanged);
  question?.addEventListener('input', markDraftChanged);
  form?.addEventListener('dragover', (event) => event.preventDefault());
  form?.addEventListener('drop', (event) => {
    event.preventDefault();
    if (!attachmentInput || !event.dataTransfer?.files.length) return;
    attachmentInput.files = event.dataTransfer.files;
    renderAttachments();
  });
  question?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      form?.requestSubmit();
    }
  });
  form?.addEventListener('submit', () => {
    draftChanged = false;
    if (submitButton) submitButton.disabled = true;
    if (submitLabel) submitLabel.textContent = 'Analisando…';
    if (status) status.textContent = 'Consultando dados e fontes…';
  });
  document.querySelectorAll('[data-feedback-form]').forEach((feedbackForm) => {
    feedbackForm.addEventListener('submit', () => {
      const button = feedbackForm.querySelector('button[type="submit"]');
      if (button) {
        button.disabled = true;
        button.textContent = 'Salvando…';
      }
    });
  });
  window.addEventListener('beforeunload', (event) => {
    if (!draftChanged) return;
    event.preventDefault();
    event.returnValue = '';
  });
  if (document.querySelector('.field-error')) question?.focus();
})();
