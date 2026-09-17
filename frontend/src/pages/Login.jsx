import React from 'react'
import {useState} from 'react';
import {useNavigate} from 'react-router-dom';

const Login = ({onLoginSuccess=()=>{}}) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

    const handleLogin = async (e, demoUsername, demoPassword) => {
        e.preventDefault();
        try{
            const response = await fetch(`${import.meta.env.VITE_API_URL}/auth/login`, {
                method: 'POST', 
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: demoUsername || username,
                    password: demoPassword || password,
                })
            });
            if(!response.ok){
                setError("Invalid username or password");
                return;
            }
            const data = await response.json();
            localStorage.setItem('token', data.access_token);
            onLoginSuccess(data.access_token);
            navigate('/dashboard');
        }catch(err){
            setError("Something went wrong, try again");
        }
    };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className='w-full max-w-md'>

            <div className='text-center mb-8'>
                <h1 className='text-3xl font-semibold text-gray-800'>Ticket Triage</h1>
                <p className='text-gray-500 text-sm mt-2'>Customer service, simplified.</p>
            </div>

            <div className='bg-white border border-gray-200 rounded-2xl p-8'>
                <h2 className='text-lg text-gray-700 font-medium mb-4'>Sign in to your account</h2>
                {error && (
                    <div className="bg-red-50 border border-red-300 text-red-600 text-sm px-4 py-3 m-4 rounded-lg">
                        {error}
                    </div>
                )}
                <form onSubmit={handleLogin}>
                    <div className='mb-4'>
                        <label className='text-xs text-gray-500 block-mb-1'>Username</label>
                        <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
                            type='text'
                            value={username}
                            onChange={(e)=>setUsername(e.target.value)}
                            placeholder='demoName'
                            required
                        />
                    </div>
                    <div className='mb-6'>
                        <label className="text-xs text-gray-500 block-mb-1">Password</label>
                        <input className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-400"
                        type='password'
                        value={password}
                        onChange={(e)=>setPassword(e.target.value)}
                        placeholder='********'
                        required
                        />
                    </div>
                    <button type="submit"
                    className='w-full h-8 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-800'
                    >
                        Sign in
                    </button>
                </form>
            </div>
        </div>
      
    </div>
  )
}

export default Login
