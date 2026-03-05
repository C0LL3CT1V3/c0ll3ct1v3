import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useApiClient } from '../hooks/useApiClient';

function Accounts() {
  const apiClient = useApiClient();
  const [accounts, setAccounts] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    account_name: '',
    bank_name: '',
    account_number: '',
    routing_number: '',
    account_type: 'checking',
    current_balance: 0
  });

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const response = await apiClient.get('/accounts/');
      setAccounts(response.data);
      setError('');
    } catch (error) {
      console.error('Error fetching accounts:', error);
      setError(error?.response?.data?.detail || 'Failed to load accounts.');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await apiClient.post('/accounts/', formData);
      setShowForm(false);
      setFormData({
        account_name: '',
        bank_name: '',
        account_number: '',
        routing_number: '',
        account_type: 'checking',
        current_balance: 0
      });
      fetchAccounts();
    } catch (error) {
      console.error('Error creating account:', error);
      setError(error?.response?.data?.detail || 'Failed to create account.');
    }
  };

  return (
    <div className="container">
      <nav className="nav">
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/accounts">Bank Accounts</Link>
        <Link to="/wallets">Crypto Wallets</Link>
        <Link to="/ledgers">Ledgers</Link>
        <Link to="/documents">Documents</Link>
      </nav>

      <h1>Bank Accounts</h1>
      {error ? <div className="error-message">{error}</div> : null}
      
      <button className="btn" onClick={() => setShowForm(!showForm)}>
        {showForm ? 'Cancel' : 'Add New Account'}
      </button>

      {showForm && (
        <form onSubmit={handleSubmit} style={{ marginTop: '1rem', maxWidth: '500px' }}>
          <div className="form-group">
            <label>Account Name:</label>
            <input
              type="text"
              value={formData.account_name}
              onChange={(e) => setFormData({...formData, account_name: e.target.value})}
              required
            />
          </div>
          
          <div className="form-group">
            <label>Bank Name:</label>
            <input
              type="text"
              value={formData.bank_name}
              onChange={(e) => setFormData({...formData, bank_name: e.target.value})}
              required
            />
          </div>
          
          <div className="form-group">
            <label>Account Number:</label>
            <input
              type="text"
              value={formData.account_number}
              onChange={(e) => setFormData({...formData, account_number: e.target.value})}
              required
            />
          </div>
          
          <div className="form-group">
            <label>Routing Number:</label>
            <input
              type="text"
              value={formData.routing_number}
              onChange={(e) => setFormData({...formData, routing_number: e.target.value})}
              required
            />
          </div>
          
          <div className="form-group">
            <label>Account Type:</label>
            <select
              value={formData.account_type}
              onChange={(e) => setFormData({...formData, account_type: e.target.value})}
            >
              <option value="checking">Checking</option>
              <option value="savings">Savings</option>
              <option value="business">Business</option>
            </select>
          </div>
          
          <div className="form-group">
            <label>Current Balance:</label>
            <input
              type="number"
              step="0.01"
              value={formData.current_balance}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  current_balance: e.target.value === '' ? 0 : parseFloat(e.target.value),
                })
              }
            />
          </div>
          
          <button type="submit" className="btn">Create Account</button>
        </form>
      )}

      <div style={{ marginTop: '2rem' }}>
        <h2>Your Accounts</h2>
        {accounts.length === 0 ? (
          <p>No accounts found. Add your first account above.</p>
        ) : (
          <div style={{ display: 'grid', gap: '1rem' }}>
            {accounts.map(account => (
              <div key={account.id} style={{ border: '1px solid #ddd', padding: '1rem', borderRadius: '8px', textAlign: 'left' }}>
                <h3>{account.account_name}</h3>
                <p><strong>Bank:</strong> {account.bank_name}</p>
                <p><strong>Type:</strong> {account.account_type}</p>
                <p><strong>Balance:</strong> ${account.current_balance.toFixed(2)}</p>
                <p><strong>Account #:</strong> {account.account_number}</p>
                <p><strong>Routing #:</strong> {account.routing_number}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Accounts;
