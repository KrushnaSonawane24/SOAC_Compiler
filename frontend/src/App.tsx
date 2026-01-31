/**
 * SOAC Frontend App
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute } from './auth/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { NewJobPage } from './pages/NewJobPage';
import { JobDetailPage } from './pages/JobDetailPage';
import { ThemeProvider } from './theme/ThemeContext';
import { AmbientBackground } from './components/AmbientBackground';
import { MascotProvider } from './mascot/MascotContext';
import { SoacChan } from './components/SoacChan';
import './index.css';

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <MascotProvider>
            <div className="relative min-h-screen">
              <AmbientBackground />
              <div className="relative z-10 min-h-screen">
                <Routes>
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/register" element={<RegisterPage />} />

                  <Route
                    path="/"
                    element={
                      <ProtectedRoute>
                        <DashboardPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/new"
                    element={
                      <ProtectedRoute>
                        <NewJobPage />
                      </ProtectedRoute>
                    }
                  />
                  <Route
                    path="/jobs/:jobId"
                    element={
                      <ProtectedRoute>
                        <JobDetailPage />
                      </ProtectedRoute>
                    }
                  />

                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </div>
              <SoacChan />
            </div>
          </MascotProvider>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
