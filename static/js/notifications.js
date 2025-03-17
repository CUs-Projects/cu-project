document.addEventListener('DOMContentLoaded', function() {
    // Notification button and panel elements
    const notificationBtn = document.getElementById('notification-btn');
    const notificationsPanel = document.getElementById('notifications-panel');
    const markAllReadBtn = document.getElementById('mark-all-read');

    // Toggle notifications panel
    if (notificationBtn) {
        notificationBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            notificationsPanel.classList.toggle('hidden');
        });
    }

    // Close panel when clicking outside
    document.addEventListener('click', function(e) {
        if (!notificationsPanel.contains(e.target) && e.target !== notificationBtn) {
            notificationsPanel.classList.add('hidden');
        }
    });

    // Mark individual notification as read
    document.querySelectorAll('.notification-item.unread').forEach(item => {
        item.addEventListener('click', function() {
            const notificationId = this.dataset.notificationId;
            fetch(`/notifications/${notificationId}/read`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.classList.remove('unread');
                    updateNotificationBadge();
                }
            });
        });
    });

    // Mark all as read
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', function() {
            fetch('/mark_notifications_read', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.querySelectorAll('.notification-item').forEach(item => {
                        item.classList.remove('unread');
                    });
                    const badge = document.getElementById('notification-badge');
                    if (badge) {
                        badge.remove();
                    }
                    notificationsPanel.classList.add('hidden');
                }
            });
        });
    }
});

function updateNotificationBadge() {
    const badge = document.getElementById('notification-badge');
    const unreadCount = document.querySelectorAll('.notification-item.unread').length;
    if (badge) {
        if (unreadCount === 0) {
            badge.remove();
        } else {
            badge.textContent = unreadCount;
        }
    }
}