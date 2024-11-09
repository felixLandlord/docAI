// function toggleModal() {
//     document.getElementById('uploadModal').classList.toggle('active');
// }
function toggleModal() {
    var modal = document.getElementById('uploadModal');
    modal.style.display = modal.style.display === 'block' ? 'none' : 'block';
}

// Scroll to bottom when new messages are added
document.body.addEventListener('htmx:afterSwap', function() {
    const messages = document.getElementById('messages');
    if (messages) {
        messages.scrollTop = messages.scrollHeight;
    }
});

// Add loading state
document.body.addEventListener('htmx:beforeRequest', function(evt) {
    if (evt.detail.elt.closest('form')) {
        evt.detail.elt.querySelector('button[type="submit"]').disabled = true;
    }
});

document.body.addEventListener('htmx:afterRequest', function(evt) {
    if (evt.detail.elt.closest('form')) {
        evt.detail.elt.querySelector('button[type="submit"]').disabled = false;
        if (evt.detail.successful) {
            toggleModal();
        }
    }
});