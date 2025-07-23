# Romanian Freight Forwarder - Style Guide

> **Visual Design System for Enterprise Logistics Management**

This style guide defines the visual language, components, and design patterns for the Romanian Freight Forwarder automation system. It ensures consistency, accessibility, and professional appearance across all user interfaces.

---

## 🎨 **CORE DESIGN PRINCIPLES**

### **Professional Excellence**
- Clean, enterprise-grade interfaces that inspire confidence
- Minimal distractions to support focused work environments
- Clear visual hierarchy for quick information processing

### **Operational Efficiency** 
- Status-driven design with immediate visual feedback
- Consistent patterns that reduce cognitive load
- Responsive design for desktop-primary, mobile-aware usage

### **Romanian Business Standards**
- Professional European business aesthetic
- Compliance-ready interface design
- Multilingual typography considerations

---

## 🎯 **COLOR PALETTE**

### **Primary Colors**
```
Primary Blue:    #2563eb (bg-blue-600)    - Main brand, CTAs, links
Primary Dark:    #1d4ed8 (bg-blue-700)    - Hover states, emphasis  
Primary Light:   #3b82f6 (bg-blue-500)    - Backgrounds, highlights
```

### **Secondary Colors**
```
Secondary Gray:  #64748b (bg-slate-500)    - Secondary actions, text
Secondary Dark:  #475569 (bg-slate-600)    - Secondary hover states
Secondary Light: #94a3b8 (bg-slate-400)    - Disabled states, borders
```

### **Status Colors**
```
Success Green:   #059669 (bg-emerald-600)  - Completed, confirmed
Success Light:   #10b981 (bg-emerald-500)  - Success backgrounds
Warning Orange:  #d97706 (bg-amber-600)    - Pending, warnings
Warning Light:   #f59e0b (bg-amber-500)    - Warning backgrounds  
Error Red:       #dc2626 (bg-red-600)      - Errors, cancellations
Error Light:     #ef4444 (bg-red-500)      - Error backgrounds
Info Blue:       #0891b2 (bg-cyan-600)     - Information, in-progress
Info Light:      #06b6d4 (bg-cyan-500)     - Info backgrounds
```

### **Neutral Colors**
```
White:           #ffffff (bg-white)        - Cards, modals, clean backgrounds
Gray 50:         #f8fafc (bg-slate-50)     - Page backgrounds
Gray 100:        #f1f5f9 (bg-slate-100)    - Subtle backgrounds
Gray 200:        #e2e8f0 (bg-slate-200)    - Borders, dividers
Gray 300:        #cbd5e1 (bg-slate-300)    - Input borders
Gray 400:        #94a3b8 (bg-slate-400)    - Placeholder text
Gray 500:        #64748b (bg-slate-500)    - Secondary text
Gray 600:        #475569 (bg-slate-600)    - Primary text
Gray 700:        #334155 (bg-slate-700)    - Headings
Gray 800:        #1e293b (bg-slate-800)    - High contrast text
Gray 900:        #0f172a (bg-slate-900)    - Headers, strong emphasis
```

---

## 📝 **TYPOGRAPHY**

### **Font Families**
```css
Primary Font:    Inter, system-ui, -apple-system, sans-serif
Monospace:       'JetBrains Mono', Consolas, 'Courier New', monospace
```

### **Font Scale (Tailwind Classes)**
```
Heading 1:       text-3xl font-bold (30px)      - Page titles
Heading 2:       text-2xl font-semibold (24px)  - Section headers  
Heading 3:       text-xl font-semibold (20px)   - Subsection headers
Heading 4:       text-lg font-medium (18px)     - Component titles
Body Large:      text-base font-normal (16px)   - Primary body text
Body Regular:    text-sm font-normal (14px)     - Secondary text
Body Small:      text-xs font-normal (12px)     - Captions, metadata
Button Text:     text-sm font-medium (14px)     - All button text
Label Text:      text-sm font-medium (14px)     - Form labels
```

### **Line Heights**
```
Tight:           leading-tight (1.25)          - Headings
Normal:          leading-normal (1.5)          - Body text  
Relaxed:         leading-relaxed (1.625)       - Long-form content
```

---

## 📏 **SPACING SYSTEM**

### **Base Unit**: 4px (Tailwind's default)

### **Common Spacing Values**
```
xs:   4px   (space-1)     - Tight element spacing
sm:   8px   (space-2)     - Small gaps, padding
md:   16px  (space-4)     - Standard spacing
lg:   24px  (space-6)     - Section spacing  
xl:   32px  (space-8)     - Large section gaps
2xl:  48px  (space-12)    - Page section spacing
3xl:  64px  (space-16)    - Major layout spacing
```

### **Component Spacing**
```
Button Padding:     px-4 py-2 (16px horizontal, 8px vertical)
Input Padding:      px-3 py-2 (12px horizontal, 8px vertical)
Card Padding:       p-6 (24px all sides)
Modal Padding:      p-6 (24px all sides)
Page Padding:       px-4 md:px-6 lg:px-8 (responsive)
```

---

## 🔲 **COMPONENT STYLES**

### **Buttons**

#### **Primary Button**
```css
Classes: bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-md transition-colors
Use: Main actions, form submissions, confirmations
```

#### **Secondary Button**  
```css
Classes: bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium px-4 py-2 rounded-md transition-colors
Use: Secondary actions, cancellations
```

#### **Danger Button**
```css
Classes: bg-red-600 hover:bg-red-700 text-white font-medium px-4 py-2 rounded-md transition-colors  
Use: Destructive actions, deletions, cancellations
```

#### **Outline Button**
```css
Classes: border border-slate-300 hover:border-slate-400 text-slate-700 font-medium px-4 py-2 rounded-md transition-colors
Use: Tertiary actions, toggles
```

### **Form Inputs**

#### **Text Input**
```css
Classes: border border-slate-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 px-3 py-2 rounded-md text-sm
Placeholder: text-slate-400
```

#### **Select Dropdown**
```css
Classes: border border-slate-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 px-3 py-2 rounded-md text-sm bg-white
```

#### **Form Labels**
```css
Classes: block text-sm font-medium text-slate-700 mb-1
```

### **Cards & Containers**

#### **Standard Card**
```css
Classes: bg-white rounded-lg border border-slate-200 p-6 shadow-sm
Use: Content containers, order cards, forms
```

#### **Highlighted Card**
```css
Classes: bg-blue-50 border border-blue-200 rounded-lg p-6
Use: Important information, featured content
```

### **Status Badges**

#### **Status Badge Base**
```css
Classes: inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium
```

#### **Status Variations**
```css
Pending:     bg-amber-100 text-amber-800
In Progress: bg-cyan-100 text-cyan-800  
Completed:   bg-emerald-100 text-emerald-800
Cancelled:   bg-red-100 text-red-800
Assigned:    bg-blue-100 text-blue-800
```

---

## 📊 **ORDER MANAGEMENT SPECIFIC STYLES**

### **Order Status Colors**
```
pending:               text-amber-600 bg-amber-50
assigned:              text-blue-600 bg-blue-50
in_transit:            text-purple-600 bg-purple-50
awaiting_documents:    text-orange-600 bg-orange-50
documents_received:    text-indigo-600 bg-indigo-50
documents_validated:   text-teal-600 bg-teal-50
client_invoiced:       text-cyan-600 bg-cyan-50
payment_received:      text-emerald-600 bg-emerald-50
subcontractor_paid:    text-green-600 bg-green-50
completed:             text-emerald-700 bg-emerald-100
cancelled:             text-red-600 bg-red-50
disputed:              text-rose-600 bg-rose-50
```

### **Priority Indicators**
```
High Priority:    border-l-4 border-red-500
Medium Priority:  border-l-4 border-amber-500  
Low Priority:     border-l-4 border-slate-300
```

### **Financial Indicators**
```
Profit Positive:  text-emerald-600
Profit Negative:  text-red-600
Profit Neutral:   text-slate-600
Currency Symbol:  text-slate-500 font-medium
```

---

## 🎛️ **LAYOUT PATTERNS**

### **Page Layout**
```css
Main Container:   max-w-7xl mx-auto px-4 sm:px-6 lg:px-8
Section Spacing:  space-y-6
Grid Layout:      grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6
```

### **Header Navigation**
```css
Header:           bg-white border-b border-slate-200 px-4 py-3
Nav Links:        text-slate-600 hover:text-slate-900 px-3 py-2 font-medium
Active Link:      text-blue-600 border-b-2 border-blue-600
```

### **Sidebar Navigation**
```css
Sidebar:          bg-slate-50 border-r border-slate-200 w-64
Sidebar Item:     text-slate-700 hover:bg-slate-100 px-3 py-2 rounded-md
Active Item:      bg-blue-100 text-blue-700
```

---

## 📱 **RESPONSIVE DESIGN**

### **Breakpoints** (Tailwind defaults)
```
sm:   640px   - Small tablets, large phones
md:   768px   - Tablets, small laptops  
lg:   1024px  - Laptops, desktops
xl:   1280px  - Large desktops
2xl:  1536px  - Extra large screens
```

### **Mobile-First Patterns**
```
Mobile:    Single column, full-width cards, stacked navigation
Tablet:    Two-column grids, collapsible sidebar
Desktop:   Multi-column layouts, persistent sidebar, advanced filtering
```

---

## ♿ **ACCESSIBILITY STANDARDS**

### **Color Contrast**
- **Minimum**: 4.5:1 for normal text (WCAG AA)
- **Enhanced**: 7:1 for normal text (WCAG AAA)
- **Large Text**: 3:1 minimum ratio

### **Focus States**
```css
Focus Ring:       focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
Focus Visible:    focus-visible:outline-none focus-visible:ring-2
```

### **Interactive Elements**
- Minimum touch target: 44px × 44px
- Clear focus indicators for all interactive elements
- Semantic HTML elements (button, input, select)

---

## 🔄 **ANIMATION & TRANSITIONS**

### **Standard Transitions**
```css
Default:          transition-colors duration-200
Hover Effects:    hover:transition-all hover:duration-150
Loading States:   animate-pulse, animate-spin
```

### **Animation Guidelines**
- **Subtle**: Enhance UX without distraction
- **Fast**: 150-200ms for micro-interactions
- **Purposeful**: Support user understanding of state changes

---

## 🎭 **TONE & VOICE**

### **Visual Personality**
- **Professional**: Clean, organized, business-appropriate
- **Efficient**: Information-dense but not cluttered
- **Trustworthy**: Consistent, predictable, reliable
- **International**: Modern European business standards

### **Iconography**
- **Style**: Outline icons (Lucide React)
- **Size**: 16px, 20px, 24px standard sizes
- **Weight**: Medium stroke width (1.5-2px)
- **Color**: Inherit from parent or text-slate-500

---

## ✅ **IMPLEMENTATION NOTES**

### **Tailwind CSS Integration**
This style guide is designed to work seamlessly with Tailwind CSS utility classes. All color values, spacing, and component patterns map directly to Tailwind utilities.

### **Component Library**
Integrate with shadcn/ui components using these style definitions as the base theme configuration.

### **Customization**
```javascript
// tailwind.config.js theme extension
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6', 
          600: '#2563eb',
          700: '#1d4ed8'
        }
      }
    }
  }
}
```

---

**Created**: 2025-01-18  
**Version**: 1.0  
**Status**: Active  
**Next Review**: Upon major feature additions

