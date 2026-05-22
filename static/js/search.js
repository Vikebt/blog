(function() {
    let searchIndex = [];

    function getBaseUrl() {
        var meta = document.querySelector('meta[name="base-url"]');
        return meta ? meta.getAttribute('content') : '';
    }

    async function loadSearchIndex() {
        try {
            var baseUrl = getBaseUrl();
            const res = await fetch(baseUrl + '/search-index.json');
            searchIndex = await res.json();
        } catch (e) {
            console.warn('Search index not available');
        }
    }

    function performSearch(query) {
        if (!query.trim() || searchIndex.length === 0) {
            return [];
        }

        const q = query.toLowerCase().trim();
        return searchIndex.filter(function(item) {
            return item.title.toLowerCase().includes(q)
                || item.content.toLowerCase().includes(q)
                || item.tags.some(function(t) { return t.toLowerCase().includes(q); })
                || item.description.toLowerCase().includes(q);
        }).slice(0, 20);
    }

    function renderResults(results) {
        const container = document.getElementById('search-results');
        if (!container) return;

        if (results.length === 0) {
            container.innerHTML = '<div class="search-no-results">没有找到匹配的文章</div>';
            return;
        }

        container.innerHTML = results.map(function(item) {
            return '<a href="' + item.url + '" class="search-result-item">'
                + '<div class="search-result-title">' + escapeHtml(item.title) + '</div>'
                + '<div class="search-result-meta">'
                + (item.tags.length ? item.tags.map(function(t) { return '#' + t; }).join(' ') : '')
                + (item.date ? ' · ' + item.date : '')
                + '</div>'
                + '</a>';
        }).join('');
    }

    function escapeHtml(str) {
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    document.addEventListener('DOMContentLoaded', function() {
        loadSearchIndex();

        var toggleBtn = document.getElementById('search-toggle');
        var overlay = document.getElementById('search-overlay');
        var closeBtn = document.getElementById('search-close');
        var input = document.getElementById('search-input');

        if (!toggleBtn || !overlay) return;

        function openSearch() {
            overlay.style.display = 'flex';
            setTimeout(function() { if (input) input.focus(); }, 100);
            document.body.style.overflow = 'hidden';
        }

        function closeSearch() {
            overlay.style.display = 'none';
            document.body.style.overflow = '';
            if (input) input.value = '';
            var results = document.getElementById('search-results');
            if (results) results.innerHTML = '';
        }

        toggleBtn.addEventListener('click', openSearch);
        if (closeBtn) closeBtn.addEventListener('click', closeSearch);

        // Close on overlay click (not on container click)
        overlay.addEventListener('click', function(e) {
            if (e.target === overlay) closeSearch();
        });

        // Close on Escape
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && overlay.style.display === 'flex') {
                closeSearch();
            }
        });

        // Ctrl+K / Cmd+K to open
        document.addEventListener('keydown', function(e) {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                if (overlay.style.display !== 'flex') {
                    openSearch();
                }
            }
        });

        // Live search with debounce
        if (input) {
            var debounceTimer;
            input.addEventListener('input', function() {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(function() {
                    var results = performSearch(input.value);
                    renderResults(results);
                }, 200);
            });
        }
    });
})();
