'use strict';
const registrationEntry = document.getElementById('registration-entry');
const registrationDialog = document.getElementById('registration-dialog');
registrationEntry.addEventListener('click', () => registrationDialog.showModal());
registrationDialog.addEventListener('click', (event) => {
  if (event.target !== registrationDialog) return;
  const rect = registrationDialog.getBoundingClientRect();
  if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) registrationDialog.close();
});
