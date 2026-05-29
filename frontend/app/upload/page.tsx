'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function UploadPage() {
    const router = useRouter();
    const [file, setFile] = useState<File | null>(null);
    const [description, setDescription] = useState('');
    const [tags, setTags] = useState('');
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState('');
    const [preview, setPreview] = useState<string | null>(null);
    const [authToken, setAuthToken] = useState<string | null>(null);

    useEffect(() => {
        const token = localStorage.getItem('authToken');
        if (token) {
            setAuthToken(token);
        }
    }, []);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (selectedFile) {
            setFile(selectedFile);
            setError('');

            const reader = new FileReader();
            reader.onloadend = () => {
                setPreview(reader.result as string);
            };
            reader.readAsDataURL(selectedFile);
        }
    };

    const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile && droppedFile.type.startsWith('image/')) {
            setFile(droppedFile);
            setError('');

            const reader = new FileReader();
            reader.onloadend = () => {
                setPreview(reader.result as string);
            };
            reader.readAsDataURL(droppedFile);
        } else {
            setError('Please drop an image file');
        }
    };

    const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
    };

    const handleLogout = () => {
        localStorage.removeItem('authToken');
        setAuthToken(null);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!file) {
            setError('Please select a file');
            return;
        }

        setUploading(true);
        setError('');

        try {
            const formData = new FormData();
            formData.append('file', file);

            if (description) {
                formData.append('description', description);
            }

            if (tags) {
                const tagArray = tags.split(',').map(tag => tag.trim()).filter(tag => tag);
                tagArray.forEach(tag => {
                    formData.append('tags', tag);
                });
            }

            const response = await fetch('http://localhost:8000/images/', {
                method: 'POST',
                body: formData,
                headers: authToken ? { Authorization: `Bearer ${authToken}` } : undefined,
            });

            if (!response.ok) {
                const body = await response.json().catch(() => null);
                throw new Error(body?.detail || 'Upload failed');
            }

            const data = await response.json();
            console.log('Upload successful:', data);
            router.push('/gallery');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to upload image. Make sure the backend is running.');
            console.error(err);
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="min-h-screen p-8">
            <div className="max-w-3xl mx-auto">
                <div className="mb-8">
                    <div className="flex items-center justify-between gap-4 mb-4 rounded-2xl border border-purple-500/20 bg-purple-900/80 px-4 py-3 text-sm text-gray-200">
                        {authToken ? (
                            <>
                                <span className="text-cyan-300">Logged in with saved session</span>
                                <button type="button" onClick={handleLogout} className="text-purple-200 hover:text-white">
                                    Log out
                                </button>
                            </>
                        ) : (
                            <span className="text-gray-300">
                                Upload anonymously or <Link href="/login" className="text-cyan-300 hover:text-cyan-200">log in</Link> to save uploads.
                            </span>
                        )}
                    </div>
                    <Link
                        href="/"
                        className="text-cyan-400 hover:text-cyan-300 transition-colors inline-flex items-center gap-2 mb-4"
                    >
                        ← Back to Home
                    </Link>
                    <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-400 via-cyan-400 to-purple-400 bg-clip-text text-transparent">
                        Upload Image
                    </h1>
                    <p className="text-gray-300 mt-2">
                        Upload your photo and let AI generate tags automatically
                    </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div
                        onDrop={handleDrop}
                        onDragOver={handleDragOver}
                        className="border-2 border-dashed border-purple-500/50 rounded-lg p-8 text-center hover:border-purple-400 transition-colors bg-purple-900/10"
                    >
                        {preview ? (
                            <div className="space-y-4">
                                <img
                                    src={preview}
                                    alt="Preview"
                                    className="max-h-64 mx-auto rounded-lg shadow-lg shadow-purple-500/20"
                                />
                                <p className="text-sm text-gray-300">{file?.name}</p>
                                <button
                                    type="button"
                                    onClick={() => {
                                        setFile(null);
                                        setPreview(null);
                                    }}
                                    className="text-cyan-400 hover:text-cyan-300 text-sm"
                                >
                                    Change Image
                                </button>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <div className="text-6xl">📸</div>
                                <div>
                                    <label htmlFor="file-upload" className="cursor-pointer">
                                        <span className="text-cyan-400 hover:text-cyan-300 font-semibold">
                                            Click to upload
                                        </span>
                                        <span className="text-gray-300"> or drag and drop</span>
                                    </label>
                                    <input
                                        id="file-upload"
                                        type="file"
                                        accept="image/*"
                                        onChange={handleFileChange}
                                        className="hidden"
                                    />
                                </div>
                                <p className="text-sm text-gray-400">PNG, JPG, GIF up to 10MB</p>
                            </div>
                        )}
                    </div>

                    <div>
                        <label htmlFor="description" className="block text-sm font-medium text-purple-300 mb-2">
                            Description (Optional)
                        </label>
                        <textarea
                            id="description"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            rows={3}
                            className="w-full px-4 py-2 bg-purple-900/20 border border-purple-500/30 rounded-lg focus:outline-none focus:border-purple-400 text-gray-100 placeholder-gray-500"
                            placeholder="Describe your image..."
                        />
                    </div>

                    <div>
                        <label htmlFor="tags" className="block text-sm font-medium text-purple-300 mb-2">
                            Tags (Optional)
                        </label>
                        <input
                            id="tags"
                            type="text"
                            value={tags}
                            onChange={(e) => setTags(e.target.value)}
                            className="w-full px-4 py-2 bg-purple-900/20 border border-purple-500/30 rounded-lg focus:outline-none focus:border-purple-400 text-gray-100 placeholder-gray-500"
                            placeholder="landscape, sunset, beach (comma separated)"
                        />
                        <p className="text-xs text-gray-400 mt-1">
                            AI will automatically generate additional tags
                        </p>
                    </div>

                    {error && (
                        <div className="bg-red-500/10 border border-red-500/50 text-red-300 px-4 py-3 rounded-lg">
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={uploading || !file}
                        className="w-full bg-gradient-to-r from-purple-600 to-cyan-600 hover:from-purple-500 hover:to-cyan-500 disabled:from-gray-600 disabled:to-gray-600 text-white font-semibold py-3 px-6 rounded-lg transition-all duration-300 disabled:cursor-not-allowed shadow-lg shadow-purple-500/50 hover:shadow-purple-500/70"
                    >
                        {uploading ? 'Uploading...' : 'Upload Image'}
                    </button>
                </form>
            </div>
        </div>
    );
}
