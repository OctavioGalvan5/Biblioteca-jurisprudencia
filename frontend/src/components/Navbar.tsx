'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BookOpen, Upload, Search } from 'lucide-react';

export default function Navbar() {
  const pathname = usePathname();

  const links = [
    { href: '/sentencias', label: 'Biblioteca', icon: BookOpen },
    { href: '/cargar', label: 'Cargar Sentencia', icon: Upload },
  ];

  return (
    <header className="bg-purple-950 shadow-lg shadow-purple-950/20 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/sentencias" className="flex items-center gap-3">
            <div className="bg-purple-500 p-1.5 rounded-lg">
              <BookOpen className="h-5 w-5 text-white" />
            </div>
            <div>
              <span className="text-white font-semibold text-lg tracking-wide">
                Biblioteca Jurisprudencia
              </span>
              <span className="hidden sm:block text-purple-300 text-xs">
                Estudio Toyos &amp; Espin
              </span>
            </div>
          </Link>

          {/* Nav links */}
          <nav className="flex items-center gap-1">
            {links.map(({ href, label, icon: Icon }) => {
              const active = pathname === href;
              return (
                <Link
                  key={href}
                  href={href}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                    active
                      ? 'bg-purple-600 text-white shadow-sm shadow-purple-500/30'
                      : 'text-purple-200 hover:bg-purple-900 hover:text-white'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
}
