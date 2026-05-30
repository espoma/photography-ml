'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface Image {
    id: number;
    filename: string;
    file_path: string;
    description: string | null;
    tags: string[];
    created_at: string;
}

export default function GalleryPage() {
    const [images, setImages] = useState<Image[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [currentUser, setCurrentUser] = useState<{ username: string } | null>(null);
    const [selectedImage, setSelectedImage] = useState<Image | null>(null);

    useEffect(() => {
        const token = localStorage.getItem('authToken');
        if (token) {
            verifyCurrentUser(token);
        }
        fetchImages();
    }, []);

    const verifyCurrentUser = async (token: string) => {
        try {
            const response = await fetch('http://localhost:8000/auth/me', {
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });

            if (response.status === 401) {
                // Token is invalid, clear it
                localStorage.removeItem('authToken');
                setCurrentUser(null);
                return;
            }

            if (!response.ok) {
                // Network or server error, but don't clear token
                console.error('Failed to verify auth token:', response.status, response.statusText);
                return;
            }

            const data = await response.json();
            setCurrentUser(data);
        } catch (err) {
            // Network error, don't clear token - could be temporary
            console.error('Network error checking auth:', err);
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('authToken');
        setCurrentUser(null);
    };

    const fetchImages = async () => {
        try {
            const response = await fetch('http://localhost:8000/images/');
            if (!response.ok) {
                throw new Error('Failed to fetch images');
            }
            const data = await response.json();
            setImages(data);
        } catch (err) {
            setError('Failed to load images. Make sure the backend is running.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm('Are you sure you want to delete this image?')) {
            return;
        }

        try {
            const response = await fetch(`http://localhost:8000/images/${id}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                throw new Error('Failed to delete image');
            }

            // Remove from local state
            setImages(images.filter(img => img.id !== id));
            setSelectedImage(null);
        } catch (err) {
            alert('Failed to delete image');
            console.error(err);
        }
    };

    return (
        <div className="min-h-screen p-8">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-8 flex justify-between items-center">
                    <div>
                        <Link
                            href="/"
                            className="text-cyan-400 hover:text-cyan-300 transition-colors inline-flex items-center gap-2 mb-4"
                        >
                            ← Back to Home
                        </Link>
                        <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-400 via-cyan-400 to-purple-400 bg-clip-text text-transparent">
                            Gallery
                        </h1>
                        <p className="text-gray-300 mt-2">
                            {images.length} {images.length === 1 ? 'image' : 'images'} in your collection
                        </p>
                        {currentUser ? (
                            <p className="text-gray-300 mt-2">
                                Logged in as <span className="text-cyan-300">{currentUser.username}</span>
                            </p>
                        ) : (
                            <p className="text-gray-300 mt-2">
                                Viewing images anonymously. <Link href="/login" className="text-cyan-300 hover:text-cyan-200">Log in</Link> to save uploads.
                            </p>
                        )}
                    </div>
                    {currentUser ? (
                        <button
                            onClick={handleLogout}
                            className="bg-red-600 hover:bg-red-500 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
                        >
                            Log out
                        </button>
                    ) : null}
                    <Link
                        href="/upload"
                        className="bg-gradient-to-r from-purple-600 to-cyan-600 hover:from-purple-500 hover:to-cyan-500 text-white font-semibold py-2 px-6 rounded-lg transition-all duration-300 shadow-lg shadow-purple-500/50"
                    >
                        + Upload New
                    </Link>
                </div>

                {/* Loading State */}
                {loading && (
                    <div className="text-center py-12">
                        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-purple-400"></div>
                        <p className="text-gray-300 mt-4">Loading images...</p>
                    </div>
                )}

                {/* Error State */}
                {error && (
                    <div className="bg-red-500/10 border border-red-500/50 text-red-300 px-4 py-3 rounded-lg">
                        {error}
                    </div>
                )}

                {/* Empty State */}
                {!loading && !error && images.length === 0 && (
                    <div className="text-center py-12 border-2 border-dashed border-purple-500/30 rounded-lg">
                        <div className="text-6xl mb-4">🖼️</div>
                        <h3 className="text-xl font-semibold text-purple-300 mb-2">No images yet</h3>
                        <p className="text-gray-400 mb-6">Upload your first image to get started</p>
                        <Link
                            href="/upload"
                            className="inline-block bg-gradient-to-r from-purple-600 to-cyan-600 hover:from-purple-500 hover:to-cyan-500 text-white font-semibold py-2 px-6 rounded-lg transition-all duration-300"
                        >
                            Upload Image
                        </Link>
                    </div>
                )}

                {/* Gallery Grid */}
                {!loading && !error && images.length > 0 && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {images.map((image) => (
                            <div
                                key={image.id}
                                onClick={() => setSelectedImage(image)}
                                className="group cursor-pointer bg-purple-900/10 border border-purple-500/30 rounded-lg overflow-hidden hover:border-purple-400 hover:shadow-lg hover:shadow-purple-500/50 transition-all duration-300"
                            >
                                <div className="aspect-square relative overflow-hidden bg-purple-900/20">
                                    <img
                                        src={`http://localhost:8000${image.file_path}`}
                                        alt={image.description || 'Gallery image'}
                                        className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
                                    />
                                </div>
                                <div className="p-4">
                                    {image.description && (
                                        <p className="text-gray-200 text-sm mb-2 line-clamp-2">
                                            {image.description}
                                        </p>
                                    )}
                                    <div className="flex flex-wrap gap-2">
                                        {image.tags.slice(0, 3).map((tag, idx) => (
                                            <span
                                                key={idx}
                                                className="text-xs bg-purple-500/20 text-purple-300 px-2 py-1 rounded"
                                            >
                                                {tag}
                                            </span>
                                        ))}
                                        {image.tags.length > 3 && (
                                            <span className="text-xs text-gray-400">
                                                +{image.tags.length - 3} more
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}

                {/* Image Modal */}
                {selectedImage && (
                    <div
                        className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4"
                        onClick={() => setSelectedImage(null)}
                    >
                        <div
                            className="bg-gradient-to-br from-purple-900/90 to-cyan-900/90 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-auto"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <div className="p-6">
                                <div className="flex justify-between items-start mb-4">
                                    <h2 className="text-2xl font-bold text-purple-300">Image Details</h2>
                                    <button
                                        onClick={() => setSelectedImage(null)}
                                        className="text-gray-400 hover:text-white text-2xl"
                                    >
                                        ×
                                    </button>
                                </div>

                                <img
                                    src={`http://localhost:8000${selectedImage.file_path}`}
                                    alt={selectedImage.description || 'Image'}
                                    className="w-full rounded-lg mb-4 shadow-2xl"
                                />

                                {selectedImage.description && (
                                    <div className="mb-4">
                                        <h3 className="text-sm font-semibold text-purple-300 mb-1">Description</h3>
                                        <p className="text-gray-200">{selectedImage.description}</p>
                                    </div>
                                )}

                                <div className="mb-4">
                                    <h3 className="text-sm font-semibold text-purple-300 mb-2">Tags</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {selectedImage.tags.map((tag, idx) => (
                                            <span
                                                key={idx}
                                                className="bg-purple-500/30 text-purple-200 px-3 py-1 rounded-full text-sm"
                                            >
                                                {tag}
                                            </span>
                                        ))}
                                    </div>
                                </div>

                                <div className="mb-4">
                                    <h3 className="text-sm font-semibold text-purple-300 mb-1">Uploaded</h3>
                                    <p className="text-gray-300 text-sm">
                                        {new Date(selectedImage.created_at).toLocaleString()}
                                    </p>
                                </div>

                                <div className="flex gap-3">
                                    <button
                                        onClick={() => handleDelete(selectedImage.id)}
                                        className="flex-1 bg-red-600 hover:bg-red-500 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
                                    >
                                        Delete Image
                                    </button>
                                    <button
                                        onClick={() => setSelectedImage(null)}
                                        className="flex-1 bg-purple-600 hover:bg-purple-500 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
                                    >
                                        Close
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
