document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-product-autocomplete]').forEach((input) => {
        const form = input.closest('form');
        const suggestions = form?.querySelector('[data-product-suggestions]');
        const endpoint = input.dataset.suggestionsUrl;
        if (!form || !suggestions || !endpoint) {
            return;
        }

        let timer;
        let activeIndex = -1;
        let controller;

        const closeSuggestions = () => {
            suggestions.replaceChildren();
            suggestions.hidden = true;
            activeIndex = -1;
        };

        const chooseSuggestion = (productName) => {
            input.value = productName;
            closeSuggestions();
            form.requestSubmit();
        };

        const renderSuggestions = (products) => {
            suggestions.replaceChildren();
            activeIndex = -1;

            products.forEach((product, index) => {
                const option = document.createElement('button');
                option.type = 'button';
                option.className = 'inventory-product-suggestion';
                option.setAttribute('role', 'option');
                option.dataset.index = String(index);

                const name = document.createElement('strong');
                name.textContent = product.product_name;
                option.append(name);

                const details = document.createElement('span');
                details.textContent = [product.product_company, product.product_packing]
                    .filter(Boolean)
                    .join(' · ');
                option.append(details);

                option.addEventListener('click', () => chooseSuggestion(product.product_name));
                option.addEventListener('mouseenter', () => setActive(index));
                suggestions.append(option);
            });

            suggestions.hidden = products.length === 0;
            input.setAttribute('aria-expanded', String(products.length > 0));
        };

        const setActive = (index) => {
            const options = [...suggestions.querySelectorAll('.inventory-product-suggestion')];
            activeIndex = index;
            options.forEach((option, optionIndex) => {
                const active = optionIndex === activeIndex;
                option.classList.toggle('active', active);
                option.setAttribute('aria-selected', String(active));
            });
            options[activeIndex]?.scrollIntoView({ block: 'nearest' });
        };

        input.addEventListener('input', () => {
            clearTimeout(timer);
            controller?.abort();

            const query = input.value.trim();
            if (query.length < 2) {
                closeSuggestions();
                input.setAttribute('aria-expanded', 'false');
                return;
            }

            timer = setTimeout(async () => {
                controller = new AbortController();
                const requestController = controller;
                const url = new URL(endpoint, window.location.origin);
                url.searchParams.set('q', query);

                try {
                    const response = await fetch(url, { signal: requestController.signal });
                    if (!response.ok) {
                        throw new Error(`Product suggestions request failed (${response.status}).`);
                    }
                    const data = await response.json();
                    if (controller !== requestController || input.value.trim() !== query) {
                        return;
                    }
                    renderSuggestions(data.products || []);
                } catch (error) {
                    if (error.name === 'AbortError') {
                        return;
                    }
                    console.error(error);
                    closeSuggestions();
                    const message = document.createElement('div');
                    message.className = 'inventory-product-suggestion-error';
                    message.textContent = 'Could not load product suggestions. Please try searching again.';
                    suggestions.append(message);
                    suggestions.hidden = false;
                    input.setAttribute('aria-expanded', 'true');
                }
            }, 250);
        });

        input.addEventListener('keydown', (event) => {
            const options = suggestions.querySelectorAll('.inventory-product-suggestion');
            if (event.key === 'Escape') {
                closeSuggestions();
                input.setAttribute('aria-expanded', 'false');
            } else if (options.length && event.key === 'ArrowDown') {
                event.preventDefault();
                setActive((activeIndex + 1) % options.length);
            } else if (options.length && event.key === 'ArrowUp') {
                event.preventDefault();
                setActive(activeIndex <= 0 ? options.length - 1 : activeIndex - 1);
            } else if (options.length && event.key === 'Enter' && activeIndex >= 0) {
                event.preventDefault();
                chooseSuggestion(options[activeIndex].querySelector('strong').textContent);
            }
        });

        document.addEventListener('click', (event) => {
            if (!form.contains(event.target)) {
                closeSuggestions();
                input.setAttribute('aria-expanded', 'false');
            }
        });
    });
});
