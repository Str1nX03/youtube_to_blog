document.addEventListener('DOMContentLoaded', () => {
    const navBtn = document.getElementById('nav-cta');
    const heroBtn = document.getElementById('hero-cta');

    function goToApp() {
        window.location.href = '/app';
    }

    navBtn.addEventListener('click', goToApp);
    heroBtn.addEventListener('click', goToApp);
});