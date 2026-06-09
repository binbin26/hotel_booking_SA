// fix_font.js - Chạy 1 lần duy nhất để sửa triệt để lỗi tách chữ "ế, ấ, ố"
(function() {
    const injectFontFix = () => {
        // 1. Tự động kiểm tra và sửa các link Google Fonts bị thiếu subset Tiếng Việt
        const links = document.querySelectorAll('link[href*="fonts.googleapis.com/css"]');
        links.forEach(link => {
            let href = link.getAttribute('href');
            if (href && !href.includes('subset=vietnamese')) {
                // Ép Google Fonts tải thêm gói font Tiếng Việt mở rộng
                link.setAttribute('href', href + '&subset=vietnamese&display=swap');
            }
        });

        // 2. Tạo thẻ style ép toàn bộ hệ thống dùng font dự phòng chuẩn nếu font chính bị lỗi glyph
        const style = document.createElement('style');
        style.id = 'vietnamese-font-fix-css';
        style.textContent = `
            /* Ép font hệ thống chuẩn hỗ trợ 100% tiếng Việt cho tất cả các thẻ text */
            body, html, p, span, a, h1, h2, h3, h4, h5, h6, div, li, button, input, td, th {
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
                letter-spacing: normal !important; /* Triệt tiêu hoàn toàn thuộc tính giãn chữ gây vỡ dấu */
                text-rendering: optimizeLegibility !important;
                -webkit-font-smoothing: antialiased !important;
            }
        `;
        
        // Đảm bảo không bị chèn trùng lặp
        if (!document.getElementById('vietnamese-font-fix-css')) {
            document.head.appendChild(style);
        }
    };

    // Chạy ngay lập tức hoặc đợi DOM sẵn sàng
    if (document.head) {
        injectFontFix();
    } else {
        document.addEventListener('DOMContentLoaded', injectFontFix);
    }
})();