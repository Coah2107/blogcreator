# Dark Mode Documentation

## Overview

The BlogCreator module now includes comprehensive dark mode support that provides a professional, eye-friendly interface for users who prefer dark themes.

## Features

### Automatic Theme Detection
- The module automatically detects your system's theme preference
- If your system is set to dark mode, the BlogCreator will start in dark mode
- If your system is set to light mode, the BlogCreator will start in light mode

### Manual Theme Toggle
- A toggle button appears in the top-right corner of the interface
- Click the button to switch between light and dark modes
- The button shows a moon icon in light mode and a sun icon in dark mode

### Persistent User Preference
- Your theme choice is automatically saved in your browser's local storage
- The next time you visit the BlogCreator, it will remember your preference
- Your preference takes priority over system theme detection

## Components with Dark Mode Support

### Blog Content (.ai-content)
- Headers, paragraphs, and text elements
- Code blocks with syntax highlighting
- Blockquotes with accent colors
- Tables with alternating row colors
- Images with proper contrast

### Kanban Cards (.bc_kanban_card)
- Card backgrounds and borders
- Title and description text
- Hover effects and shadows

### Form Elements
- Input fields and text areas
- Labels and form controls
- Buttons and navigation elements
- Dropdown menus and modals

### Odoo Backend Integration
- Navigation bars and control panels
- List and tree views
- Form views and notebooks
- Breadcrumbs and search bars

## CSS Variables

The dark mode implementation uses CSS custom properties for easy theming:

### Background Colors
- `--bg-primary`: Main background color
- `--bg-secondary`: Secondary background color
- `--bg-tertiary`: Tertiary background color
- `--bg-hover`: Hover state background
- `--bg-code`: Code block background
- `--bg-table-header`: Table header background
- `--bg-table-row`: Table row background

### Text Colors
- `--text-primary`: Primary text color
- `--text-secondary`: Secondary text color
- `--text-tertiary`: Tertiary text color
- `--text-muted`: Muted text color
- `--text-light`: Light text color
- `--text-heading`: Heading text color
- `--text-subheading`: Subheading text color

### Border Colors
- `--border-primary`: Primary border color
- `--border-secondary`: Secondary border color
- `--border-tertiary`: Tertiary border color
- `--border-accent`: Accent border color
- `--border-hover`: Hover state border color

### Shadow Colors
- `--shadow-light`: Light shadow
- `--shadow-medium`: Medium shadow
- `--shadow-heavy`: Heavy shadow
- `--shadow-button`: Button shadow

## Customization

### Adding Custom Dark Mode Styles

If you want to add custom dark mode styles to your own components:

```css
/* Light mode styles */
.my-component {
  background-color: var(--bg-primary);
  color: var(--text-primary);
  border: 1px solid var(--border-primary);
}

/* Dark mode specific styles */
[data-theme="dark"] .my-component {
  /* Add specific dark mode overrides if needed */
}
```

### Extending the Theme Toggle

You can extend the dark mode toggle functionality by listening to theme changes:

```javascript
// Listen for theme changes
document.addEventListener('DOMContentLoaded', function() {
  const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
      if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
        const theme = document.documentElement.getAttribute('data-theme');
        console.log('Theme changed to:', theme);
        // Your custom logic here
      }
    });
  });

  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme']
  });
});
```

## Browser Support

The dark mode implementation is compatible with all modern browsers that support:
- CSS custom properties (variables)
- CSS attribute selectors
- Local storage
- Modern JavaScript features

## Accessibility

The dark mode implementation follows accessibility best practices:
- High contrast ratios between text and background
- Proper focus indicators
- Consistent color scheme throughout the interface
- Support for users with visual impairments
- Respects user's system preferences

## Troubleshooting

### Theme Not Switching
- Check browser console for JavaScript errors
- Ensure the dark_mode_toggle.js file is loaded properly
- Verify that local storage is enabled in your browser

### Styles Not Applying
- Ensure dark_mode.css is loaded after other CSS files
- Check that CSS custom properties are supported in your browser
- Verify the data-theme attribute is being set on the html element

### Performance Issues
- The theme switching uses CSS transitions for smooth animations
- If you experience performance issues, you can disable transitions by adding:
```css
* {
  transition: none !important;
}
```

## Development

When developing new features or components, remember to:
1. Use CSS custom properties for colors and theme-dependent values
2. Test both light and dark modes
3. Ensure proper contrast ratios
4. Follow the existing variable naming conventions
5. Consider accessibility requirements

## Support

If you encounter any issues with the dark mode implementation:
1. Check the browser console for errors
2. Verify all CSS and JavaScript files are loaded
3. Test in different browsers
4. Check for conflicts with other modules or custom CSS

The dark mode feature enhances the user experience by providing a comfortable viewing option for different lighting conditions and personal preferences.