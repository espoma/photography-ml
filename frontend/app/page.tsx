import Image from "next/image";
import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm lg:flex">
        <p className="fixed left-0 top-0 flex w-full justify-center border-b border-purple-500/50 bg-gradient-to-b from-purple-900/80 to-transparent pb-6 pt-8 backdrop-blur-2xl lg:static lg:w-auto lg:rounded-xl lg:border lg:border-purple-500/50 lg:bg-purple-900/30 lg:p-4">
          Photography Portfolio&nbsp;
          <code className="font-mono font-bold text-cyan-400">v0.1.0</code>
        </p>
      </div>

      <div className="relative flex place-items-center before:absolute before:h-[300px] before:w-[480px] before:-translate-x-1/2 before:rounded-full before:bg-gradient-radial before:from-purple-600 before:to-transparent before:opacity-20 before:blur-3xl after:absolute after:-z-20 after:h-[180px] after:w-[240px] after:translate-x-1/3 after:bg-gradient-conic after:from-cyan-500 after:via-purple-500 after:to-cyan-500 after:opacity-30 after:blur-3xl before:lg:h-[360px] z-[-1]">
        <h1 className="text-6xl font-bold tracking-tighter sm:text-7xl bg-gradient-to-r from-purple-400 via-cyan-400 to-purple-400 bg-clip-text text-transparent">
          AI Gallery
        </h1>
      </div>

      <div className="mb-32 grid text-center lg:max-w-5xl lg:w-full lg:mb-0 lg:grid-cols-4 lg:text-left mt-20 gap-4">
        <Link
          href="/upload"
          className="group rounded-lg border border-purple-500/30 bg-purple-900/10 px-5 py-4 transition-all duration-300 hover:border-purple-400 hover:bg-purple-900/30 hover:shadow-lg hover:shadow-purple-500/50"
        >
          <h2 className="mb-3 text-2xl font-semibold text-purple-300">
            Upload{" "}
            <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none text-cyan-400">
              -&gt;
            </span>
          </h2>
          <p className="m-0 max-w-[30ch] text-sm text-gray-300">
            Upload new photos to your AI-powered portfolio.
          </p>
        </Link>

        <Link
          href="/gallery"
          className="group rounded-lg border border-purple-500/30 bg-purple-900/10 px-5 py-4 transition-all duration-300 hover:border-purple-400 hover:bg-purple-900/30 hover:shadow-lg hover:shadow-purple-500/50"
        >
          <h2 className="mb-3 text-2xl font-semibold text-purple-300">
            Gallery{" "}
            <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none text-cyan-400">
              -&gt;
            </span>
          </h2>
          <p className="m-0 max-w-[30ch] text-sm text-gray-300">
            View your curated collection of images.
          </p>
        </Link>
      </div>
    </main>
  );
}
