function scrollToElementById(id) {
    const targetElement = document.getElementById(id);
    const targetPosition = targetElement.getBoundingClientRect().top + window.scrollY;
    const offset = 100; // Adjust this value for desired spacing
    console.log(targetPosition - offset)
    window.scrollTo({
        top: targetPosition - offset,
    });
}

export { scrollToElementById };
window.scrollToElementById = scrollToElementById;