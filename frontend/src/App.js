import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import Accounts from './pages/Accounts';
import Wallets from './pages/Wallets';
import Ledgers from './pages/Ledgers';
import Documents from './pages/Documents';
import ProtectedRoute from './components/ProtectedRoute';

// Helper function to convert kebab-case/snake_case to PascalCase
// Example: "example-page" or "example_page" -> "ExamplePage"
function toPascalCase(str) {
  if (!str) return '';
  return str
    .split(/[-_]/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join('') + 'Page';
}

// Helper function to get subdomain from hostname
const getSubdomain = () => {
  const host = window.location.host;
  const parts = host.split('.');
  if (parts[0] === 'localhost' || parts[0] === '127') {
    // Handle localhost:3000 or sub.localhost:3000
    return parts[1]?.split(':')[0] || '';
  }
  // Handle production: app.example.com -> "app"
  return parts.length > 2 ? parts[0] : '';
};

// Get available custom pages context
const customPagesContext = require.context('./pages', false, /\.js$/);
const availablePages = customPagesContext.keys().map(filename => 
  filename.replace('./', '').replace('.js', '')
);

function App() {
  const [subdomainPage, setSubdomainPage] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const subdomain = getSubdomain();
    
    if (subdomain) {
      // Convert subdomain to PascalCase page name (e.g., "example" -> "ExamplePage")
      const pageName = toPascalCase(subdomain);
      
      // Check if the page exists
      if (availablePages.includes(pageName)) {
        try {
          // Dynamically import only the matching page
          const pageModule = customPagesContext(`./${pageName}.js`);
          setSubdomainPage(pageModule.default);
        } catch (error) {
          console.error(`Failed to load page for subdomain "${subdomain}":`, error);
          setSubdomainPage(null);
        }
      } else {
        console.log(`No page found for subdomain "${subdomain}" (looking for ${pageName}.js)`);
        setSubdomainPage(null);
      }
    } else {
      // No subdomain, show regular app
      setSubdomainPage(null);
    }
    
    setIsLoading(false);
  }, []);

  // If there's a subdomain and a matching page, show only that page
  if (isLoading) {
    return <div className="App">Loading...</div>;
  }

  if (subdomainPage) {
    // Create a component wrapper since JSX requires capitalized component names
    const SubdomainPageComponent = subdomainPage;
    
    return (
      <Router>
        <div className="App">
          <Routes>
            <Route path="*" element={<SubdomainPageComponent />} />
          </Routes>
        </div>
      </Router>
    );
  }

  // No subdomain or no matching page - show regular app routes
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } />
          <Route path="/accounts" element={
            <ProtectedRoute>
              <Accounts />
            </ProtectedRoute>
          } />
          <Route path="/wallets" element={
            <ProtectedRoute>
              <Wallets />
            </ProtectedRoute>
          } />
          <Route path="/ledgers" element={
            <ProtectedRoute>
              <Ledgers />
            </ProtectedRoute>
          } />
          <Route path="/documents" element={
            <ProtectedRoute>
              <Documents />
            </ProtectedRoute>
          } />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
