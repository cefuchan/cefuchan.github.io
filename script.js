// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault()
    const target = document.querySelector(this.getAttribute("href"))
    if (target) {
      target.scrollIntoView({
        behavior: "smooth",
        block: "start",
      })
    }
  })
})

// Header scroll effect
window.addEventListener("scroll", () => {
  const header = document.querySelector(".header")
  if (window.scrollY > 50) {
    header.style.background = "rgba(255, 255, 255, 0.98)"
    header.style.boxShadow = "0 2px 20px rgba(0, 0, 0, 0.1)"
  } else {
    header.style.background = "rgba(255, 255, 255, 0.95)"
    header.style.boxShadow = "0 1px 3px rgba(0, 0, 0, 0.1)"
  }
})

// Intersection Observer for animations
const observerOptions = {
  threshold: 0.1,
  rootMargin: "0px 0px -50px 0px",
}

const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = "1"
      entry.target.style.transform = "translateY(0)"
    }
  })
}, observerOptions)

// Animate elements on scroll
document.addEventListener("DOMContentLoaded", () => {
  const animatedElements = document.querySelectorAll(
    ".analysis-card, .insight-card, .timeline-item, .service-item, .target-card",
  )

  animatedElements.forEach((el, index) => {
    el.style.opacity = "0"
    el.style.transform = "translateY(30px)"
    el.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`
    observer.observe(el)
  })
})

// Number animation
function animateNumbers() {
  const numbers = document.querySelectorAll(".metric-number, .target-number")

  numbers.forEach((number) => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const finalText = entry.target.textContent
          const numericValue = Number.parseInt(finalText.replace(/[^\d]/g, ""))

          if (numericValue && numericValue > 0) {
            animateNumber(entry.target, 0, numericValue, finalText)
          }
          observer.unobserve(entry.target)
        }
      })
    })

    observer.observe(number)
  })
}

function animateNumber(element, start, end, originalText) {
  const duration = 2000
  const startTime = performance.now()

  function update(currentTime) {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / duration, 1)
    const easeOutQuart = 1 - Math.pow(1 - progress, 4)

    const current = Math.floor(start + (end - start) * easeOutQuart)
    element.textContent = originalText.replace(/\d+/, current)

    if (progress < 1) {
      requestAnimationFrame(update)
    }
  }

  requestAnimationFrame(update)
}

// Initialize animations
document.addEventListener("DOMContentLoaded", () => {
  animateNumbers()
})

// Button click handlers
document.addEventListener("DOMContentLoaded", () => {
  const primaryBtn = document.querySelector(".btn-primary")
  const secondaryBtn = document.querySelector(".btn-secondary")

  if (primaryBtn) {
    primaryBtn.addEventListener("click", () => {
      // Create a more professional modal or redirect
      if (confirm("Proje başlatma talebi göndermek istediğinizden emin misiniz?")) {
        alert("Talebiniz alındı! 24 saat içinde size dönüş yapacağız.")
      }
    })
  }

  if (secondaryBtn) {
    secondaryBtn.addEventListener("click", () => {
      if (confirm("Detaylı görüşme randevusu almak istediğinizden emin misiniz?")) {
        alert("Randevu talebiniz alındı! Size uygun saatleri paylaşacağız.")
      }
    })
  }
})

// Image lazy loading fallback
document.addEventListener("DOMContentLoaded", () => {
  const images = document.querySelectorAll(".metric-image")

  images.forEach((img) => {
    img.addEventListener("error", () => {
      img.style.display = "none"
      const container = img.closest(".visual-container")
      if (container) {
        container.innerHTML =
          '<div style="padding: 2rem; text-align: center; color: #6c757d; background: #f8f9fa;">Görsel yükleniyor...</div>'
      }
    })
  })
})
