
(function() {
    var resourceCache  = {};
    var readyCallbacks = [];

    function load(urlOrArr) {
        if (urlOrArr instanceof Array) {
            urlOrArr.forEach(function(url) { _load(url); });
        } else {
            _load(urlOrArr);
        }
    }

    function _load(url) {
        if (resourceCache[url]) {
            return resourceCache[url];
        }
        var img = new Image();

        img.onload = function() {
            resourceCache[url] = img;
            if (isReady()) {
                readyCallbacks.forEach(function(func) { func(); });
            }
        };

        
        img.onerror = function() {
            resourceCache[url] = 'missing';
            if (isReady()) {
                readyCallbacks.forEach(function(func) { func(); });
            }
        };

        resourceCache[url] = false;
        img.src = url;
    }

    
    function get(url) {
        var cached = resourceCache[url];
        return (cached && cached !== 'missing') ? cached : null;
    }

    function isReady() {
        for (var k in resourceCache) {
            if (resourceCache.hasOwnProperty(k) && !resourceCache[k]) {
                return false;   
            }
        }
        return true;
    }

    function onReady(func) { readyCallbacks.push(func); }

    window.Resources = { load: load, get: get, onReady: onReady, isReady: isReady };
})();
