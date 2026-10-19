import { Link } from "react-router-dom";
import { Compass } from "lucide-react";

export default function NotFound() {
  return (
    <div className="card grid place-items-center px-6 py-20 text-center">
      <Compass size={38} className="text-accent" />
      <h2 className="mt-4 text-xl font-bold text-white">Страницата не е намерена</h2>
      <p className="mt-2 max-w-md text-sm text-slate-400">
        Проверете адреса или се върнете към dashboard-а.
      </p>
      <Link to="/" className="btn-primary mt-5">
        Към Dashboard
      </Link>
    </div>
  );
}
