document.addEventListener('DOMContentLoaded', () => {

    // --- Theme Toggle Functionality ---
    const themeToggle = document.querySelector('.theme-toggle');
    const body = document.body;
    
    // Initialize theme from localStorage or default to dark
    const savedTheme = localStorage.getItem('theme') || 'dark';
    body.setAttribute('data-theme', savedTheme);
    
    // Handle theme toggle
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = body.getAttribute('data-theme') || 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            body.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }

    // --- Intersection Observer for Scroll Animations ---
    const observerOptions = {
        root: null, // relative to the viewport
        rootMargin: '0px',
        threshold: 0.1 // trigger when 10% of the element is visible
    };

    const observerCallback = (entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target); // Stop observing once animated
            }
        });
    };

    const scrollObserver = new IntersectionObserver(observerCallback, observerOptions);

    // Observe elements with the 'animate-on-scroll' class
    const scrollAnimatedElements = document.querySelectorAll('.animate-on-scroll');
    scrollAnimatedElements.forEach(el => scrollObserver.observe(el));

    // --- Initial Load Animations ---
    // Add 'visible' class to elements meant to animate immediately on load
    const loadAnimatedElements = document.querySelectorAll('.animate-on-load');
    // Stagger the load animations slightly using setTimeout
    loadAnimatedElements.forEach((el, index) => {
        setTimeout(() => {
            el.classList.add('visible');
        }, index * 150); // 150ms delay between each element
    });

    // --- Smooth scrolling for anchor links ---
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            if(targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // --- Interactive elements for placeholder functionality ---
    const uploadLink = document.querySelector('.upload-link');
    const uploadArea = document.querySelector('.upload-area');
    
    if(uploadLink && uploadArea) {
        uploadLink.addEventListener('click', () => {
            // This would typically trigger a file input click
            // For now, just add a visual effect
            uploadArea.classList.add('pulse-effect');
            setTimeout(() => {
                uploadArea.classList.remove('pulse-effect');
            }, 1000);
        });
    }
    
    // --- Add pulse effect animation dynamically ---
    const style = document.createElement('style');
    style.textContent = `
        @keyframes pulse-effect {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        .pulse-effect {
            animation: pulse-effect 1s ease;
        }
    `;
    document.head.appendChild(style);
    
    // --- Optional: Dynamic text typing effect for hero subtitle ---
    const heroSubtitle = document.querySelector('.hero-text .subtitle');
    if(heroSubtitle) {
        // Store the original text
        const originalText = heroSubtitle.textContent;
        // Clear it initially
        heroSubtitle.textContent = '';
        
        // Function to type out the text
        const typeText = (text, element, speed = 50) => {
            let i = 0;
            const typing = setInterval(() => {
                if (i < text.length) {
                    element.textContent += text.charAt(i);
                    i++;
                } else {
                    clearInterval(typing);
                }
            }, speed);
        };
        
        // Start typing effect after a short delay
        setTimeout(() => {
            typeText(originalText, heroSubtitle);
        }, 500);
    }
});