import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import Accounts from './pages/Accounts';
import Wallets from './pages/Wallets';
import Ledgers from './pages/Ledgers';
import Documents from './pages/Documents';
import ProtectedRoute from './components/ProtectedRoute';

// Helper function to convert subdomain to possible page name formats
// Returns an array of possible names to check (PascalCase, lowercase, etc.)
function getPossiblePageNames(subdomain) {
  if (!subdomain) return [];
  
  // Convert to PascalCase (e.g., "archie" -> "Archie")
  const pascalCase = subdomain
    .split(/[-_]/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join('');
  
  // Return possible variations
  return [
    pascalCase,           // "Archie"
    subdomain.toLowerCase(), // "archie"
    pascalCase + 'Page',  // "ArchiePage" (in case some files use this convention)
  ];
}

// Helper function to get subdomain from hostname
const getSubdomain = () => {
  const host = window.location.host;
  const parts = host.split('.');
  if (parts[0] === 'localhost' || parts[0] === '127') {
    // Handle localhost:3000 or sub.localhost:3000
    const sub = parts[1]?.split(':')[0] || '';
    return sub.toLowerCase() === 'www' ? '' : sub;
  }
  // Handle production: app.example.com -> "app" (www is not a tenant subdomain)
  if (parts.length > 2) {
    const first = parts[0].split(':')[0];
    return first.toLowerCase() === 'www' ? '' : first;
  }
  return '';
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
      // Get possible page name variations
      const possibleNames = getPossiblePageNames(subdomain);
      
      // Find the actual page name that exists in availablePages
      // Check case-insensitively to handle variations
      const foundPageName = availablePages.find(pageName => 
        possibleNames.some(possible => 
          pageName.toLowerCase() === possible.toLowerCase()
        )
      );
      
      if (foundPageName) {
        try {
          // Dynamically import using the actual filename
          const pageModule = customPagesContext(`./${foundPageName}.js`);
          setSubdomainPage(pageModule.default);
        } catch (error) {
          console.error(`Failed to load page for subdomain "${subdomain}":`, error);
          setSubdomainPage(null);
        }
      } else {
        console.log(`No page found for subdomain "${subdomain}" (tried: ${possibleNames.join(', ')})`);
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
