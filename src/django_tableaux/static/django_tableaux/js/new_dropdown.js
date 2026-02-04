<script>
    const d = document.querySelector('.dropdown');
    const b = d.querySelector('button');

    b.addEventListener('click', () =>
    b.setAttribute('aria-expanded', d.matches(':focus-within'))
    );

    d.addEventListener('keydown', e => {
    if (e.key === 'Escape') b.blur();
});
</script>
