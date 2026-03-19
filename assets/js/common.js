// Glassmorphism navbar on scroll
(function () {
  var navbar = document.getElementById("navbar");
  if (navbar) {
    function onScroll() {
      if (window.scrollY > 10) {
        navbar.classList.add("scrolled");
      } else {
        navbar.classList.remove("scrolled");
      }
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll(); // apply on load in case page is already scrolled
  }
})();

// Smooth page transitions: fade out before navigating away
(function () {
  document.addEventListener("click", function (e) {
    var link = e.target.closest("a");
    if (
      !link ||
      !link.href ||
      link.target === "_blank" ||
      link.hasAttribute("download") ||
      e.ctrlKey ||
      e.metaKey ||
      e.shiftKey ||
      link.hostname !== window.location.hostname ||
      link.href === window.location.href ||
      link.href.startsWith(window.location.href + "#") ||
      link.classList.contains("abstract") ||
      link.classList.contains("bibtex") ||
      link.classList.contains("award")
    )
      return;

    e.preventDefault();
    document.body.classList.add("page-leaving");
    setTimeout(function () {
      window.location.href = link.href;
    }, 400);
  });
})();

$(document).ready(function () {
  // add toggle functionality to abstract, award and bibtex buttons
  $("a.abstract").click(function () {
    $(this).parent().parent().find(".abstract.hidden").toggleClass("open");
    $(this).parent().parent().find(".award.hidden.open").toggleClass("open");
    $(this).parent().parent().find(".bibtex.hidden.open").toggleClass("open");
  });
  $("a.award").click(function () {
    $(this).parent().parent().find(".abstract.hidden.open").toggleClass("open");
    $(this).parent().parent().find(".award.hidden").toggleClass("open");
    $(this).parent().parent().find(".bibtex.hidden.open").toggleClass("open");
  });
  $("a.bibtex").click(function () {
    $(this).parent().parent().find(".abstract.hidden.open").toggleClass("open");
    $(this).parent().parent().find(".award.hidden.open").toggleClass("open");
    $(this).parent().parent().find(".bibtex.hidden").toggleClass("open");
  });
  $("a").removeClass("waves-effect waves-light");

  // bootstrap-toc
  if ($("#toc-sidebar").length) {
    // remove related publications years from the TOC
    $(".publications h2").each(function () {
      $(this).attr("data-toc-skip", "");
    });
    var navSelector = "#toc-sidebar";
    var $myNav = $(navSelector);
    Toc.init($myNav);
    $("body").scrollspy({
      target: navSelector,
    });
  }

  // add css to jupyter notebooks
  const cssLink = document.createElement("link");
  cssLink.href = "../css/jupyter.css";
  cssLink.rel = "stylesheet";
  cssLink.type = "text/css";

  let theme = determineComputedTheme();

  $(".jupyter-notebook-iframe-container iframe").each(function () {
    $(this).contents().find("head").append(cssLink);

    if (theme == "dark") {
      $(this).bind("load", function () {
        $(this).contents().find("body").attr({
          "data-jp-theme-light": "false",
          "data-jp-theme-name": "JupyterLab Dark",
        });
      });
    }
  });
});
