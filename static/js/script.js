document.addEventListener("DOMContentLoaded", function () {
    console.log("AgroGuide loaded successfully");

    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll(".nav-right a");

    navLinks.forEach(link => {
        const linkPath = new URL(link.href).pathname;

        if (linkPath === currentPath) {
            link.style.textDecoration = "underline";
            link.style.textUnderlineOffset = "4px";
        }
    });
});