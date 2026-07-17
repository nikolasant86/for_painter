document.addEventListener('DOMContentLoaded', function() {
    // === 1. МОБИЛЬНОЕ МЕНЮ ===
    const menuToggle = document.querySelector('.menu-toggle');
    const navigationButtons = document.querySelector('.navigation-buttons');

    if (menuToggle && navigationButtons) {
        menuToggle.addEventListener('click', function() {
            navigationButtons.classList.toggle('active');
            menuToggle.textContent = navigationButtons.classList.contains('active') ? '✕' : '☰';
        });
    }

    // === 2. ДИНАМИЧЕСКАЯ ЗАГРУЗКА ГАЛЕРЕИ И МОДАЛЬНОЕ ОКНО ===
    const galleryContainer = document.getElementById('gallery-container');
    const modal = document.getElementById('myModal');
    const modalImg = document.getElementById('modalImg');
    const closeBtn = document.querySelector('.close');
    const resetBtn = document.getElementById('resetBtn');

    // Находим и скрываем старые кнопки навигации, если они остались в HTML
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    if (prevBtn) prevBtn.style.display = 'none';
    if (nextBtn) nextBtn.style.display = 'none';
    if (resetBtn) resetBtn.style.display = 'none'

    let images = [];
    let currentIndex = 0;
    
    // Параметры масштабирования (зума)
    let scale = 1;
    const maxScale = 3;
    const minScale = 0.5;
    const scaleStep = 0.1;

    if (typeof currentProject !== 'undefined' && galleryContainer) {
        loadProjectGallery(currentProject);
    }

    // Функция загрузки галереи
    async function loadProjectGallery(projectId) {
        try {
            images = [];
            galleryContainer.innerHTML = '';

            for (let i = 1; i <= 30; i++) {
                const imageNum = String(i).padStart(2, '0');
                const imageId = `${projectId}/${imageNum}`;

                const response = await fetch(`/api/image?image_id=${imageId}`);
                
                if (response.status === 404) {
                    break;
                }

                if (response.ok) {
                    const data = await response.json();
                    images.push(data.url);

                    const galleryItem = document.createElement('div');
                    galleryItem.className = 'gallery';
                    
                    const img = document.createElement('img');
                    img.src = data.url;
                    img.alt = `Иллюстрация ${imageNum}`;
                    img.loading = 'lazy';

                    const itemIndex = images.length - 1;
                    img.addEventListener('click', () => openModal(itemIndex));

                    galleryItem.appendChild(img);
                    galleryContainer.appendChild(galleryItem);
                }
            }

            if (images.length === 0) {
                galleryContainer.innerHTML = '<p class="error">В этой папке пока нет иллюстраций.</p>';
            }

        } catch (error) {
            console.error('Ошибка загрузки галереи:', error);
            galleryContainer.innerHTML = '<p class="error">Не удалось загрузить галерею. Попробуйте позже.</p>';
        }
    }

    // === ЛОГИКА МОДАЛЬНОГО ОКНА ===

    function openModal(index) {
        currentIndex = index;
        modalImg.src = images[currentIndex];
        modal.classList.add('show');
        modal.style.display = 'block';
        resetScale(); 
    }

    function closeModal() {
        modal.classList.remove('show');
        modal.style.display = 'none';
    }

    if (closeBtn) closeBtn.onclick = closeModal;

    // Функции перелистывания (исправлен синтаксис JS)
    function flipNext() {
        currentIndex = (currentIndex + 1) % images.length;
        modalImg.src = images[currentIndex];
        resetScale();
    }

    function flipPrev() {
        currentIndex = (currentIndex - 1 + images.length) % images.length;
        modalImg.src = images[currentIndex];
        resetScale();
    }
    
    // Умное перелистывание по клику на экран (По четвертям экрана)
    if (modal) {
        modal.addEventListener('click', (event) => {
            if (event.target === closeBtn) return;
            if (scale > 1) return; // Блокируем листание при приближении

            // Закрытие при клике на фон (мимо картинки)
            if (event.target === modal || event.target.classList.contains('modal-content-wrapper')) {
                closeModal();
                return;
            }

            const screenWidth = window.innerWidth;
            const clickX = event.clientX;

            // Клик в правой четверти экрана — листаем вперед
            if (clickX > (screenWidth * 3) / 4) {
                flipNext();
            } 
            // Клик в левой четверти экрана — листаем назад
            else if (clickX < screenWidth / 4) {
                flipPrev();
            }
        });
    }

    // if (resetBtn) resetBtn.onclick = resetScale;

    // Навигация с клавиатуры
    document.addEventListener('keydown', (e) => {
        if (modal && (modal.classList.contains('show') || modal.style.display === 'block')) {
            if (e.key === 'Escape') closeModal();
            if (e.key === 'ArrowLeft') flipPrev();
            if (e.key === 'ArrowRight') flipNext();
            if (e.key === 'ArrowUp') zoomIn();
            if (e.key === 'ArrowDown') zoomOut();
        }
    });

    // Управление зумом колесиком мыши
    if (modalImg) {
        modalImg.addEventListener('wheel', (e) => {
            e.preventDefault();
            if (e.deltaY > 0) zoomOut();
            else zoomIn();
        }, { passive: false });
    }

    function zoomIn() {
        scale = Math.min(scale + scaleStep, maxScale);
        applyScale();
    }

    function zoomOut() {
        scale = Math.max(scale - scaleStep, minScale);
        applyScale();
    }

    function setCustomScale(value) {
        scale = value;
        applyScale();
    }

    function resetScale() {
        scale = 1;
        translateX = 0; // Сбрасываем сдвиг по горизонтали
        translateY = 0; // Сбрасываем сдвиг по вертикали
        applyScale();
    }

    function applyScale() {
        if (modalImg) {
            // Комбинируем масштаб и перемещение в одном свойстве transform
            modalImg.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
        }
    }

    // === ТАЧ-ЖЕСТЫ ДЛЯ МОБИЛЬНЫХ УСТРОЙСТВ (ЗУМ И ПЕРЕМЕЩЕНИЕ) ===
    let touchStartX = 0;
    let touchStartY = 0;
    let lastTapTime = 0;
    
    // Переменные для сдвига (панорамирования)
    let translateX = 0;
    let translateY = 0;
    let startCenterX = 0;
    let startCenterY = 0;

    if (modalImg) {
        modalImg.addEventListener('touchstart', (e) => {
            // Обработка двойного тапа (одним пальцем)
            if (e.touches.length === 1) {
                const currentTime = new Date().getTime();
                const tapLength = currentTime - lastTapTime;
                
                if (tapLength < 300 && tapLength > 0) {
                    e.preventDefault();
                    if (scale === 1) {
                        setCustomScale(1.25);
                    } else {
                        resetScale();
                    }
                }
                lastTapTime = currentTime;
            }

            // Инициализация жестов двумя пальцами (зум + сдвиг)
            if (e.touches.length === 2) {
                // Фиксируем стартовое расстояние для зума
                touchStartX = e.touches[0].clientX - e.touches[1].clientX;
                touchStartY = e.touches[0].clientY - e.touches[1].clientY;

                // Находим центральную точку между двумя пальцами в момент касания
                startCenterX = (e.touches[0].clientX + e.touches[1].clientX) / 2 - translateX;
                startCenterY = (e.touches[0].clientY + e.touches[1].clientY) / 2 - translateY;
            }
        }, { passive: false });

        modalImg.addEventListener('touchmove', (e) => {
            if (e.touches.length === 2) {
                e.preventDefault();
                
                // 1. ЛОГИКА ЗУМА (Pinch)
                let touchCurrentX = e.touches[0].clientX - e.touches[1].clientX;
                let touchCurrentY = e.touches[0].clientY - e.touches[1].clientY;

                const distanceStart = Math.sqrt(touchStartX * touchStartX + touchStartY * touchStartY);
                const distanceCurrent = Math.sqrt(touchCurrentX * touchCurrentX + touchCurrentY * touchCurrentY);

                if (distanceCurrent > distanceStart) zoomIn();
                else if (distanceCurrent < distanceStart) zoomOut();

                touchStartX = touchCurrentX;
                touchStartY = touchCurrentY;

                // 2. ЛОГИКА СДВИГА (Pan)
                // Сдвигаем картинку, только если она действительно увеличена
                if (scale > 1) {
                    const currentCenterX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
                    const currentCenterY = (e.touches[0].clientY + e.touches[1].clientY) / 2;

                    translateX = currentCenterX - startCenterX;
                    translateY = currentCenterY - startCenterY;

                    applyScale(); // Применяем сдвиг вместе с масштабом
                }
            }
        }, { passive: false });
    }
});