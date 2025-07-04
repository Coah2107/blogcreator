odoo.define('blogcreator.dark_mode_toggle', function (require) {
    'use strict';

    var core = require('web.core');
    var Widget = require('web.Widget');
    var session = require('web.session');

    var DarkModeToggle = Widget.extend({
        template: 'DarkModeToggle',
        
        init: function (parent, options) {
            this._super(parent, options);
            this.currentTheme = this.getStoredTheme();
        },

        start: function () {
            this._super();
            this.applyTheme(this.currentTheme);
            this.createToggleButton();
            return Promise.resolve();
        },

        /**
         * Get the stored theme from localStorage
         */
        getStoredTheme: function () {
            return localStorage.getItem('odoo_blogcreator_theme') || 'light';
        },

        /**
         * Store the theme in localStorage
         */
        setStoredTheme: function (theme) {
            localStorage.setItem('odoo_blogcreator_theme', theme);
        },

        /**
         * Apply the theme to the document
         */
        applyTheme: function (theme) {
            document.documentElement.setAttribute('data-theme', theme);
            this.currentTheme = theme;
        },

        /**
         * Toggle between light and dark themes
         */
        toggleTheme: function () {
            var newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
            this.applyTheme(newTheme);
            this.setStoredTheme(newTheme);
        },

        /**
         * Create the toggle button and add it to the page
         */
        createToggleButton: function () {
            var self = this;
            
            // Remove existing toggle button if it exists
            $('.dark-mode-toggle').remove();
            
            // Create toggle button HTML
            var toggleButton = $(`
                <button class="dark-mode-toggle" title="Toggle Dark Mode">
                    <i class="fa fa-moon dark-mode-toggle-icon"></i>
                    <i class="fa fa-sun dark-mode-toggle-icon"></i>
                </button>
            `);
            
            // Add click event
            toggleButton.on('click', function () {
                self.toggleTheme();
            });
            
            // Add to page
            $('body').append(toggleButton);
        },

        /**
         * Get system theme preference
         */
        getSystemTheme: function () {
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                return 'dark';
            }
            return 'light';
        },

        /**
         * Listen to system theme changes
         */
        watchSystemTheme: function () {
            var self = this;
            if (window.matchMedia) {
                var mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
                mediaQuery.addEventListener('change', function (e) {
                    var systemTheme = e.matches ? 'dark' : 'light';
                    // Only apply system theme if user hasn't set a preference
                    if (!localStorage.getItem('odoo_blogcreator_theme')) {
                        self.applyTheme(systemTheme);
                    }
                });
            }
        }
    });

    // Auto-initialize dark mode when the page loads
    $(document).ready(function () {
        var darkModeToggle = new DarkModeToggle(null, {});
        darkModeToggle.start();
        darkModeToggle.watchSystemTheme();
    });

    return DarkModeToggle;
});