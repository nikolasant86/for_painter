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

    // === 2. ЕДИНАЯ ЛОГИКА МОДАЛЬНОГО ОКНА (ПОДДЕРЖКА ФОТО И ВИДЕО) ===
    const authorModal = document.getElementById('author-modal');
    let authorModalImg = document.getElementById('author-modal-img');
    const closeAuthorBtn = document.getElementById('close-author-modal');

    // Переменные галереи и трансформаций
    let activeModalMedia = []; // Массив объектов { type: 'image'|'video', src: '...' }
    let currentModalIndex = 0;

    let isDragging = false;
    let startX = 0, startY = 0;
    let currentX = 0, currentY = 0;
    let scale = 1;
    const baseScale = 1;
    const maxScale = 4;
    const minScale = 0.8;
    let lastTapTime = 0;
    let initialPinchDistance = 0;
    let initialScaleOnPinch = 1;

    let modalPrevBtn = null;
    let modalNextBtn = null;
    let modalVideoEl = null;

    if (authorModal) {

        modalPrevBtn = authorModal.querySelector('.modal-arrow.prev');
        modalNextBtn = authorModal.querySelector('.modal-arrow.next');

        if (!modalPrevBtn) {
            modalPrevBtn = document.createElement('button');
            modalPrevBtn.className = 'modal-arrow prev';
            modalPrevBtn.innerHTML = '&#10094;';
            authorModal.appendChild(modalPrevBtn);

            modalNextBtn = document.createElement('button');
            modalNextBtn.className = 'modal-arrow next';
            modalNextBtn.innerHTML = '&#10095;';
            authorModal.appendChild(modalNextBtn);
        }

        // Создаем динамический <video> элемент для модалки, если его нет
        modalVideoEl = authorModal.querySelector('.modal-video-player');
        if (!modalVideoEl) {
            modalVideoEl = document.createElement('video');
            modalVideoEl.className = 'modal-video-player';
            modalVideoEl.controls = true;
            modalVideoEl.playsInline = true;
            modalVideoEl.style.display = 'none';
            modalVideoEl.style.maxWidth = '90vw';
            modalVideoEl.style.maxHeight = '80vh';

            const contentWrapper = authorModal.querySelector('.modal-content-wrapper') || authorModal;
            contentWrapper.appendChild(modalVideoEl);
        }

        function updateTransform() {
            if (authorModalImg && authorModalImg.style.display !== 'none') {
                authorModalImg.style.transform = `translate(${currentX}px, ${currentY}px) scale(${scale})`;
            }
        }

        function resetPosition() {
            currentX = 0;
            currentY = 0;
            scale = 1;
            if (authorModalImg) {
                authorModalImg.classList.remove('is-dragging');
                updateTransform();
            }
        }

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

        // Рендер текущего медиа в модальном окне
        function renderModalMedia() {
            if (!activeModalMedia.length) return;
            const currentItem = activeModalMedia[currentModalIndex];

            resetPosition();

            if (currentItem.type === 'video') {
                if (authorModalImg) authorModalImg.style.display = 'none';
                if (modalVideoEl) {
                    modalVideoEl.style.display = 'block';
                    modalVideoEl.src = currentItem.src;
                    modalVideoEl.play().catch(() => {});
                }
            } else {
                if (modalVideoEl) {
                    modalVideoEl.pause();
                    modalVideoEl.style.display = 'none';
                }
                if (authorModalImg) {
                    authorModalImg.style.display = 'block';
                    authorModalImg.src = currentItem.src;
                }
            }
        }

        window.openModalWithImages = function(mediaArray, startIndex = 0) {
            // Нормализуем массив (принимаем и строки, и объекты)
            activeModalMedia = mediaArray.map(item => {
                if (typeof item === 'string') {
                    const isVid = item.endsWith('.mp4') || item.endsWith('.webm') || item.endsWith('.ogg');
                    return { type: isVid ? 'video' : 'image', src: item };
                }
                return item;
            });

            currentModalIndex = startIndex;

            authorModal.classList.add('show');
            authorModal.style.display = 'flex';
            document.body.classList.add('modal-open');

            renderModalMedia();

            if (activeModalMedia.length > 1) {
                if (modalPrevBtn) modalPrevBtn.style.display = 'block';
                if (modalNextBtn) modalNextBtn.style.display = 'block';
            } else {
                if (modalPrevBtn) modalPrevBtn.style.display = 'none';
                if (modalNextBtn) modalNextBtn.style.display = 'none';
            }
        };

        function closeModal() {
            authorModal.classList.remove('show');
            authorModal.style.display = 'none';
            document.body.classList.remove('modal-open');

            if (modalVideoEl) {
                modalVideoEl.pause();
                modalVideoEl.src = '';
                modalVideoEl.style.display = 'none';
            }

            resetPosition();
            resetPageScale();
        }

        if (closeAuthorBtn) closeAuthorBtn.addEventListener('click', closeModal);

        authorModal.addEventListener('click', function(e) {
            if (e.target === authorModal || e.target.classList.contains('modal-content-wrapper')) {
                closeModal();
            }
        });

        function modalNext() {
            if (activeModalMedia.length <= 1) return;
            currentModalIndex = (currentModalIndex + 1) % activeModalMedia.length;
            renderModalMedia();
        }

        function modalPrev() {
            if (activeModalMedia.length <= 1) return;
            currentModalIndex = (currentModalIndex - 1 + activeModalMedia.length) % activeModalMedia.length;
            renderModalMedia();
        }

        if (modalNextBtn) modalNextBtn.addEventListener('click', (e) => { e.stopPropagation(); modalNext(); });
        if (modalPrevBtn) modalPrevBtn.addEventListener('click', (e) => { e.stopPropagation(); modalPrev(); });

        // Тач-события и зум для картинок в модальном окне
        if (authorModalImg) {
            function handleDoubleTap(e) {
                const currentTime = new Date().getTime();
                const tapLength = currentTime - lastTapTime;

                if (tapLength < 300 && tapLength > 0) {
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

            authorModalImg.addEventListener('touchstart', (e) => {
                handleDoubleTap(e);

                if (e.touches.length === 1) {
                    isDragging = true;
                    authorModalImg.classList.add('is-dragging');
                    startX = e.touches[0].clientX - currentX;
                    startY = e.touches[0].clientY - currentY;
                } else if (e.touches.length === 2) {
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
                    currentX = e.touches[0].clientX - startX;
                    currentY = e.touches[0].clientY - startY;
                    updateTransform();
                } else if (e.touches.length === 2 && initialPinchDistance > 0) {
                    const dx = e.touches[0].clientX - e.touches[1].clientX;
                    const dy = e.touches[0].clientY - e.touches[1].clientY;
                    const currentPinchDistance = Math.hypot(dx, dy);

                    const pinchRatio = currentPinchDistance / initialPinchDistance;
                    let newScale = initialScaleOnPinch * pinchRatio;

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
                    authorModalImg.classList.remove('is-dragging');
                    
                    if (scale < baseScale) {
                        scale = baseScale;
                        currentX = 0;
                        currentY = 0;
                        updateTransform();
                    }
                }
            });

            authorModalImg.addEventListener('mousedown', (e) => {
                if (e.button !== 0) return;
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
        }

        document.addEventListener('keydown', (e) => {
            if (authorModal && authorModal.classList.contains('show')) {
                if (e.key === 'ArrowRight') modalNext();
                if (e.key === 'ArrowLeft') modalPrev();
                if (e.key === 'Escape') closeModal();
            }
        });
    }

    // === 3. ЕДИНАЯ ИНИЦИАЛИЗАЦИЯ КАРТОЧЕК ПРОЕКТОВ ===
    const galleryItems = document.querySelectorAll('.gallery-item');

    galleryItems.forEach(item => {
        const imgEl = item.querySelector('.project-card-img') || item.querySelector('img');
        const videoEl = item.querySelector('.project-card-video');
        const prevBtn = item.querySelector('.card-arrow.prev');
        const nextBtn = item.querySelector('.card-arrow.next');

        let mediaList = [];
        const mediaData = item.getAttribute('data-media');
        const imagesData = item.getAttribute('data-images');

        if (mediaData) {
            try { mediaList = JSON.parse(mediaData); } catch(e) {}
        } else if (imagesData) {
            try {
                const rawArray = JSON.parse(imagesData);
                mediaList = rawArray.map(url => ({
                    type: url.endsWith('.mp4') || url.endsWith('.webm') || url.endsWith('.ogg') ? 'video' : 'image',
                    src: url
                }));
            } catch(e) {}
        }

        if (!mediaList.length && imgEl) {
            mediaList = [{ type: 'image', src: imgEl.src }];
        }

        let currentIndex = 0;

        function renderCardMedia(index) {
            if (index < 0) index = mediaList.length - 1;
            if (index >= mediaList.length) index = 0;
            currentIndex = index;

            const currentItem = mediaList[currentIndex];

            if (currentItem.type === 'video' && videoEl) {
                if (imgEl) imgEl.style.display = 'none';
                videoEl.style.display = 'block';
                videoEl.src = currentItem.src;
                videoEl.play().catch(() => {});
            } else if (imgEl) {
                if (videoEl) {
                    videoEl.pause();
                    videoEl.style.display = 'none';
                }
                imgEl.style.display = 'block';
                imgEl.src = currentItem.src;
            }
        }

        if (prevBtn) {
            prevBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                renderCardMedia(currentIndex - 1);
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                renderCardMedia(currentIndex + 1);
            });
        }

        // Клик по всей карточке открывает модальное окно
        item.addEventListener('click', (e) => {
            if (e.target.closest('.card-arrow')) return;

            e.preventDefault();
            if (window.openModalWithImages) {
                window.openModalWithImages(mediaList, currentIndex);
            }
        });
    });

    // Аватарка автора
    const authorLink = document.querySelector('.image-block .author-img-link');
    if (authorLink) {
        authorLink.addEventListener('click', function(e) {
            e.preventDefault();
            const imgSrc = this.getAttribute('href') || this.querySelector('img').src;
            if (window.openModalWithImages) {
                window.openModalWithImages([{ type: 'image', src: imgSrc }], 0);
            }
        });
    }

            // === 4. ОПРЕДЕЛЕНИЕ ГЕОЛОКАЦИИ, СКВОЗНОЕ ЛОГИРОВАНИЕ И ВСПОМОГАТЕЛЬНОЕ ПОПАП-ОКНО ===
    const cityPopup = document.getElementById('city-popup');
    const cityPopupText = document.getElementById('city-popup-text');
    const closeCityBtn = document.getElementById('close-city-popup');
    let cityPopupTimer = null;

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

        // Функция скрытой отправки логов на наш собственный бэкенд во Flask
        const sendSilentAnalytics = (realIp, detectedCity) => {
            fetch('/api/analytics-log', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    ip: realIp || '0.0.0.0',
                    city: detectedCity || 'Не определен',
                    url: window.location.href,
                    user_agent: navigator.userAgent
                })
            }).catch(e => console.warn('Логгер аналитики временно недоступен'));
        };

        const fetchLocation = (clientIp = '') => {
            const url = clientIp ? `/api/location?client_ip=${encodeURIComponent(clientIp)}` : '/api/location';
            
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    let finalCity = 'Неизвестный город';
                    let finalIp = clientIp || '0.0.0.0';

                    if (data.status === 'success' && data.city) {
                        finalCity = data.city;
                        finalIp = data.ip || finalIp;
                        cityPopupText.textContent = `Ваш город ${finalCity}`;
                        cityPopup.classList.remove('hidden');
                        cityPopupTimer = setTimeout(hideCityPopup, 10000);
                    }

                    // Гарантированный пуш отчета: вызывается ВСЕГДА при успешном ответе API
                    sendSilentAnalytics(finalIp, finalCity);
                })
                .catch(err => {
                    console.error('Ошибка определения местоположения:', err);
                    // Важнейшая страховка: если ваш GeoIP-сервер упал, мы ОБЯЗАНЫ отправить лог посещения
                    sendSilentAnalytics(clientIp || '192.168.1.1 (Router NAT)', 'Ошибка сервера GeoIP');
                });
        };

        // ИСПРАВЛЕНО: Стучимся строго на API эндпоинт, запрашивая формат JSON
                // ИСПРАВЛЕНО: Стучимся строго на официальный API-субдомен
        fetch('https://api.ipify.org')
            .then(res => {
                if (!res.ok) throw new Error('Сбой сети ipify API');
                return res.json();
            })
            .then(data => {
                // Передаем корректно распарсенный IP из JSON-объекта
                fetchLocation(data.ip);
            })
            .catch(err => {
                console.warn('Не удалось определить IP клиента напрямую, вызываем резервный метод сервера:', err);
                // ИСПРАВЛЕНО: Передаем пустую строку, чтобы бэкенд задействовал резервное определение
                fetchLocation('');
            });

    }

});
