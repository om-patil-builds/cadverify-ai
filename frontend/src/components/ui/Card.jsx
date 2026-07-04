const Card = ({ title, value, description, icon: Icon }) => {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6 shadow-lg shadow-slate-950/30 backdrop-blur">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-slate-400">{title}</p>
          <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
        </div>
        {Icon ? (
          <div className="rounded-xl bg-cyan-500/10 p-3 text-cyan-400">
            <Icon className="h-5 w-5" />
          </div>
        ) : null}
      </div>
      {description ? <p className="mt-3 text-sm text-slate-500">{description}</p> : null}
    </div>
  );
};

export default Card;
