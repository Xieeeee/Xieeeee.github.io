// Ambient background blob parallax on mouse move
(function () {
  var blobs = document.querySelectorAll('.blob');
  if (!blobs.length) return;

  document.addEventListener('mousemove', function (e) {
    var x = e.clientX / window.innerWidth;
    var y = e.clientY / window.innerHeight;
    blobs.forEach(function (blob, index) {
      var speed = (index + 1) * 20;
      blob.style.transform = 'translate(' + (x * speed) + 'px, ' + (y * speed) + 'px)';
    });
  });
}());
