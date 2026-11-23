// Nécessaire pour afficher des notifications sur Chrome Android (il refuse "new Notification()").
// Toucher la notification ramène sur le site.
self.addEventListener("notificationclick", e => {
  e.notification.close();
  e.waitUntil(clients.matchAll({ type: "window" }).then(l => l[0] ? l[0].focus() : clients.openWindow("./")));
});
