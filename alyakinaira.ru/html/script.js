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
    if (resetBtn) resetBtn.style.display = 'none';

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

    // Функции перелистывания
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
            modalImg.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
        }
    }

    // === ТАЧ-ЖЕСТЫ ДЛЯ МОБИЛЬНЫХ УСТРОЙСТВ ===
    let touchStartX = 0;
    let touchStartY = 0;
    let initialPinchDistance = 0;
    let initialScaleOnPinch = 1;
    let lastTapTime = 0;

    // Переменные для сдвига (панорамирования)
    let translateX = 0;
    let translateY = 0;
    let startCenterX = 0;
    let startCenterY = 0;

    if (modalImg) {
        modalImg.addEventListener('touchstart', (e) => {
            if (e.touches.length === 1) {
                const currentTime = new Date().getTime();
                const tapLength = currentTime - lastTapTime;
                
                if (tapLength < 300 && tapLength > 0) {
                    e.preventDefault();

                    if (scale < 1.45) {
                        setCustomScale(1.5);
                    } else if (scale >= 1.45 && scale < 1.95) {
                        setCustomScale(2.0);
                    } else {
                        resetScale();
                    }
                }
                lastTapTime = currentTime;
            }

            if (e.touches.length === 2) {
                e.preventDefault();

                const dx = e.touches[0].clientX - e.touches[1].clientX;
                const dy = e.touches[0].clientY - e.touches[1].clientY;
                
                initialPinchDistance = Math.hypot(dx, dy);
                initialScaleOnPinch = scale;

                startCenterX = (e.touches[0].clientX + e.touches[1].clientX) / 2 - translateX;
                startCenterY = (e.touches[0].clientY + e.touches[1].clientY) / 2 - translateY;
            }
        }, { passive: false });

        modalImg.addEventListener('touchmove', (e) => {
            if (e.touches.length === 2) {
                e.preventDefault();

                const dx = e.touches[0].clientX - e.touches[1].clientX;
                const dy = e.touches[0].clientY - e.touches[1].clientY;
                const currentPinchDistance = Math.hypot(dx, dy);

                if (initialPinchDistance > 0) {
                    const pinchRatio = currentPinchDistance / initialPinchDistance;
                    let newScale = initialScaleOnPinch * pinchRatio;
                    newScale = Math.min(Math.max(newScale, 1), 4);
                    scale = newScale;
                }

                if (scale > 1) {
                    const currentCenterX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
                    const currentCenterY = (e.touches[0].clientY + e.touches[1].clientY) / 2;

                    translateX = currentCenterX - startCenterX;
                    translateY = currentCenterY - startCenterY;
                }

                applyScale();
            }
        }, { passive: false });

        modalImg.addEventListener('touchend', (e) => {
            if (e.touches.length < 2) {
                initialPinchDistance = 0;
                if (scale < 1) {
                    resetScale();
                }
            }
        });
    }

// === 3. ОПРЕДЕЛЕНИЕ ГЕОЛОКАЦИИ И ВСПОМОГАТЕЛЬНОЕ ПОПАП-ОКНО ===
    const cityPopup = document.getElementById('city-popup');
    const cityPopupText = document.getElementById('city-popup-text');
    const closeCityBtn = document.getElementById('close-city-popup');
    let cityPopupTimer = null; // Переменная для хранения таймера автозакрытия

    // Функция скрытия окна с чисткой таймера
    const hideCityPopup = () => {
        if (cityPopup) {
            cityPopup.classList.add('hidden');
        }
        if (cityPopupTimer) {
            clearTimeout(cityPopupTimer);
            cityPopupTimer = null;
        }
    };

    if (cityPopup && cityPopupText) {
        if (closeCityBtn) {
            closeCityBtn.addEventListener('click', hideCityPopup);
        }

        // Функция запроса к нашему Flask API
        const fetchLocation = (clientIp = '') => {
            const url = clientIp ? `/api/location?client_ip=${encodeURIComponent(clientIp)}` : '/api/location';
            
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success' && data.city) {
                        cityPopupText.textContent = `Ваш город ${data.city}`;
                        cityPopup.classList.remove('hidden');

                        // Запускаем таймер скрытия на 10 секунд после показа
                        cityPopupTimer = setTimeout(hideCityPopup, 10000);
                    }
                })
                .catch(err => console.error('Ошибка определения местоположения:', err));
        };

        // Шаг 1: Пробуем узнать публичный IP напрямую из браузера клиента
        fetch('https://api.ipify.org?format=json')
            .then(res => res.json())
            .then(data => {
                // Успешно получили IP клиента, передаем во Flask
                fetchLocation(data.ip);
            })
            .catch(err => {
                console.warn('Не удалось определить IP клиента напрямую, вызываем резервный метод сервера:', err);
                // Если api.ipify недоступен или заблокирован адблокером, делаем стандартный запрос
                fetchLocation();
            });
    }

    // === МОДАЛЬНОЕ ОКНО, ДВОЙНОЙ ТАП / КЛИК И PINCH-TO-ZOOM ===
(function initAuthorModal() {
    const authorLink = document.querySelector('.image-block .author-img-link');
    const authorModal = document.getElementById('author-modal');
    const authorModalImg = document.getElementById('author-modal-img');
    const closeAuthorBtn = document.getElementById('close-author-modal');

    if (!authorLink || !authorModal || !authorModalImg) return;

    let isDragging = false;
    let startX = 0, startY = 0;
    let currentX = 0, currentY = 0;
    
    // Переменные для зума (масштабирования)
    let scale = 1;
    const baseScale = 1;
    const maxScale = 4;
    const minScale = 0.8;

    // Переменные для двойного тапа / клика
    let lastTapTime = 0;

    // Переменные для pinch-to-zoom (два пальца)
    let initialPinchDistance = 0;
    let initialScaleOnPinch = 1;

    // Сброс масштаба страницы (viewport)
    function resetPageScale() {
        const viewport = document.querySelector('meta[name="viewport"]');
        if (viewport) {
            const originalContent = viewport.getAttribute('content');
            viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0');
            setTimeout(() => {
                viewport.setAttribute('content', originalContent || 'width=device-width, initial-scale=1.0');
            }, 100);
        }
    }

    // Применение трансформации к изображению
    function updateTransform() {
        authorModalImg.style.transform = `translate(${currentX}px, ${currentY}px) scale(${scale})`;
    }

    // Сброс всех параметров к исходному состоянию
    function resetPosition() {
        currentX = 0;
        currentY = 0;
        scale = 1;
        authorModalImg.classList.remove('is-dragging');
        updateTransform();
    }

    // Открытие модального окна
    authorLink.addEventListener('click', function(e) {
        e.preventDefault();
        authorModalImg.src = this.getAttribute('href');
        authorModal.classList.add('show');
        authorModal.style.display = 'flex';
        document.body.classList.add('modal-open');
        resetPosition();
    });

    // Закрытие модального окна
    function closeModal() {
        authorModal.classList.remove('show');
        authorModal.style.display = 'none';
        document.body.classList.remove('modal-open');
        resetPosition();
        resetPageScale();
    }

    if (closeAuthorBtn) {
        closeAuthorBtn.addEventListener('click', closeModal);
    }

    authorModal.addEventListener('click', function(e) {
        if (e.target === authorModal || e.target.classList.contains('modal-content-wrapper')) {
            closeModal();
        }
    });

    // === ДВОЙНОЙ КЛИК / ТАП (+50% или 1.5x) ===
    function handleDoubleTap(e) {
        const currentTime = new Date().getTime();
        const tapLength = currentTime - lastTapTime;

        if (tapLength < 300 && tapLength > 0) {
            e.preventDefault();
            // Если изображение укрупнено — возвращаем к исходному размеру (1.0), иначе увеличиваем на 50% (1.5)
            if (scale > 1.05) {
                scale = 1;
                currentX = 0;
                currentY = 0;
            } else {
                scale = 1.5; // +50% к размеру
            }
            authorModalImg.classList.remove('is-dragging'); // Включаем плавную анимацию CSS
            updateTransform();
        }
        lastTapTime = currentTime;
    }

    authorModalImg.addEventListener('dblclick', (e) => {
        e.preventDefault();
        if (scale > 1.05) {
            scale = 1;
            currentX = 0;
            currentY = 0;
        } else {
            scale = 1.5;
        }
        authorModalImg.classList.remove('is-dragging');
        updateTransform();
    });

    // === ПЕРЕМЕЩЕНИЕ И СЕНСОРНЫЕ ЖЕСТЫ (PINCH-TO-ZOOM) ===

    authorModalImg.addEventListener('touchstart', (e) => {
        handleDoubleTap(e);

        if (e.touches.length === 1) {
            // Начало перетаскивания одним пальцем
            isDragging = true;
            authorModalImg.classList.add('is-dragging'); // Отключаем плавность на время драга для быстрого отклика
            startX = e.touches[0].clientX - currentX;
            startY = e.touches[0].clientY - currentY;
        } else if (e.touches.length === 2) {
            // Начало масштабирования двумя пальцами (Pinch)
            isDragging = false;
            authorModalImg.classList.add('is-dragging');
            const dx = e.touches[0].clientX - e.touches[1].clientX;
            const dy = e.touches[0].clientY - e.touches[1].clientY;
            initialPinchDistance = Math.hypot(dx, dy);
            initialScaleOnPinch = scale;
        }
    }, { passive: false });

    authorModalImg.addEventListener('touchmove', (e) => {
        if (e.cancelable) e.preventDefault();

        if (e.touches.length === 1 && isDragging) {
            // Перемещение пальцем
            currentX = e.touches[0].clientX - startX;
            currentY = e.touches[0].clientY - startY;
            updateTransform();
        } else if (e.touches.length === 2 && initialPinchDistance > 0) {
            // Жест сведения/разведения 2 пальцев
            const dx = e.touches[0].clientX - e.touches[1].clientX;
            const dy = e.touches[0].clientY - e.touches[1].clientY;
            const currentPinchDistance = Math.hypot(dx, dy);

            const pinchRatio = currentPinchDistance / initialPinchDistance;
            let newScale = initialScaleOnPinch * pinchRatio;

            // Ограничения зума
            scale = Math.min(Math.max(newScale, minScale), maxScale);
            updateTransform();
        }
    }, { passive: false });

    authorModalImg.addEventListener('touchend', (e) => {
        if (e.touches.length < 2) {
            initialPinchDistance = 0;
        }
        if (e.touches.length === 0) {
            isDragging = false;
            authorModalImg.classList.remove('is-dragging'); // Возвращаем плавность transition
            
            // Если сжали меньше нормального размера — плавно возвращаем к 1.0
            if (scale < baseScale) {
                scale = baseScale;
                currentX = 0;
                currentY = 0;
                updateTransform();
            }
        }
    });

    // === ПЕРЕМЕЩЕНИЕ МЫШЬЮ НА ДЕСКТОПЕ ===

    authorModalImg.addEventListener('mousedown', (e) => {
        if (e.button !== 0) return; // Только левая кнопка мыши
        isDragging = true;
        authorModalImg.classList.add('is-dragging');
        startX = e.clientX - currentX;
        startY = e.clientY - currentY;
    });

    window.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        if (e.cancelable) e.preventDefault();
        currentX = e.clientX - startX;
        currentY = e.clientY - startY;
        updateTransform();
    });

    window.addEventListener('mouseup', () => {
        if (isDragging) {
            isDragging = false;
            authorModalImg.classList.remove('is-dragging');
        }
    });
})();
});
