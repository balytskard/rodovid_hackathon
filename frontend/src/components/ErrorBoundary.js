import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary" style={{
          padding: '40px',
          textAlign: 'center',
          color: '#F44336'
        }}>
          <h2>Щось пішло не так</h2>
          <p>{this.state.error?.message || 'Невідома помилка'}</p>
          <button 
            className="btn btn-primary"
            onClick={() => window.location.reload()}
            style={{ marginTop: '16px' }}
          >
            Перезавантажити сторінку
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

