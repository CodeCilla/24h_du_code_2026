import { useState, useEffect } from 'react';

const API_URL = 'http://localhost:8080';

function App() {
  const [projects, setProjects] = useState([]);
  const [newProject, setNewProject] = useState({
    name: '',
    description: '',
    teamName: '',
  });

  // ✅ Fonction déclarée AVANT useEffect
  const fetchProjects = async () => {
    try {
      const response = await fetch(`${API_URL}/api/projects`);
      const data = await response.json();
      setProjects(data);
    } catch (error) {
      console.error('Erreur:', error);
    }
  };

  useEffect(() => {
    (async () => {
      await fetchProjects();
    })();
  }, []); // ✅ Plus d'erreur, fetchProjects est déjà déclaré

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await fetch(`${API_URL}/api/projects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newProject),
      });
      setNewProject({ name: '', description: '', teamName: '' });
      fetchProjects();
    } catch (error) {
      console.error('Erreur création:', error);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>🚀 24h du Code - Gestion des Projets</h1>

      <div
        style={{
          marginBottom: '30px',
          padding: '20px',
          background: '#f5f5f5',
          borderRadius: '8px',
          border: '1px solid #ddd',
        }}
      >
        <h2>Nouveau Projet</h2>
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '10px' }}>
            <input
              type='text'
              placeholder='Nom du projet'
              value={newProject.name}
              onChange={(e) =>
                setNewProject({ ...newProject, name: e.target.value })
              }
              style={{ padding: '8px', marginRight: '10px', width: '200px' }}
              required
            />
            <input
              type='text'
              placeholder="Nom de l'équipe"
              value={newProject.teamName}
              onChange={(e) =>
                setNewProject({ ...newProject, teamName: e.target.value })
              }
              style={{ padding: '8px', marginRight: '10px', width: '200px' }}
              required
            />
          </div>
          <div style={{ marginBottom: '10px' }}>
            <textarea
              placeholder='Description'
              value={newProject.description}
              onChange={(e) =>
                setNewProject({ ...newProject, description: e.target.value })
              }
              style={{ padding: '8px', width: '100%', minHeight: '60px' }}
            />
          </div>
          <button
            type='submit'
            style={{ padding: '8px 20px', cursor: 'pointer' }}
          >
            Créer le projet
          </button>
        </form>
      </div>

      <h2>📋 Projets existants ({projects.length})</h2>
      {projects.length === 0 ? (
        <p>Aucun projet encore. Créez-en un !</p>
      ) : (
        <div style={{ display: 'grid', gap: '15px' }}>
          {projects.map((project) => (
            <div
              key={project.id}
              style={{
                padding: '15px',
                border: '1px solid #ddd',
                borderRadius: '8px',
                background: 'white',
              }}
            >
              <h3 style={{ margin: '0 0 10px 0' }}>{project.name}</h3>
              <p style={{ margin: '5px 0', color: '#666' }}>
                <strong>Équipe:</strong> {project.teamName}
              </p>
              <p style={{ margin: '5px 0' }}>{project.description}</p>
              {project.score !== null && (
                <p style={{ margin: '5px 0', color: '#007bff' }}>
                  <strong>Score:</strong> {project.score}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default App;
