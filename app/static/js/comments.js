export function setupCommentDeletion(selector = '.delete-comment-form') {
    const deleteForms = document.querySelectorAll(selector);
    
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const confirmed = confirm('¿Estás seguro que quieres eliminar este comentario?');
            if (confirmed) {
                this.submit();  
            }
        });
    });
}