// 加载统一导航栏
window.addEventListener('load', () => {
    fetch('static/unified-header.html')
        .then(response => response.text())
        .then(data => {
            document.getElementById('header-container').innerHTML = data;
        })
        .catch(error => console.error('加载导航栏失败:', error));
});