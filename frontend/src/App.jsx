import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Terminal, Play, FileText, Activity, FolderOpen } from 'lucide-react';

const App = () => {
  const [url, setUrl] = useState('');
  const [limit, setLimit] = useState(5);
  const [logs, setLogs] = useState([]);
  const [isCrawling, setIsCrawling] = useState(false);
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const logsEndRef = useRef(null);

  const startCrawl = () => {
    if (!url) return alert("Please enter a URL");
    setIsCrawling(true);
    setLogs([]);
    
    const ws = new WebSocket("ws://localhost:8000/ws");
    
    ws.onopen = () => ws.send(JSON.stringify({ url, limit }));

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setLogs((prev) => [...prev, data]);
    };

    ws.onclose = () => {
      setIsCrawling(false);
      fetchFiles();
    };
  };

  const fetchFiles = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/files");
      const data = await res.json();
      setFiles(data);
    } catch (e) { console.error(e); }
  };

  const fetchFileContent = async (domain, filename) => {
    try {
      const res = await fetch(`http://localhost:8000/data/${domain}/${filename}`);
      const text = await res.text();
      // Replace relative image paths with backend URL for display
      const fixedText = text.replace(/\]\(images\//g, `](http://localhost:8000/data/${domain}/images/`);
      setSelectedFile({ name: filename, content: fixedText });
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  useEffect(() => {
    fetchFiles();
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans p-4 lg:p-8">
      {/* Header */}
      <header className="flex items-center gap-3 mb-8 pb-4 border-b border-slate-800">
        <Activity className="text-emerald-500 w-8 h-8" />
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Ultimate Web Crawler</h1>
          <p className="text-xs text-slate-500 font-mono">POWERED BY PYTHON & REACT</p>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-140px)]">
        
        {/* Left Panel: Control & Logs */}
        <div className="lg:col-span-4 flex flex-col gap-6 h-full">
          {/* Controls */}
          <div className="bg-slate-900 p-5 rounded-xl border border-slate-800 shadow-xl">
            <h2 className="text-sm font-semibold text-slate-400 mb-4 flex items-center gap-2 uppercase tracking-wider">
              <Terminal className="w-4 h-4" /> Crawler Config
            </h2>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-500 uppercase">Target URL</label>
                <input 
                  type="text" 
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://www.apple.com" 
                  className="w-full mt-1 bg-slate-950 border border-slate-700 rounded-lg p-3 focus:border-emerald-500 focus:outline-none text-white transition-colors"
                />
              </div>
              <div>
                <label className="text-xs font-bold text-slate-500 uppercase">Page Limit</label>
                <input 
                  type="number" 
                  value={limit}
                  onChange={(e) => setLimit(e.target.value)}
                  className="w-full mt-1 bg-slate-950 border border-slate-700 rounded-lg p-3 text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>
              <button 
                onClick={startCrawl}
                disabled={isCrawling}
                className={`w-full py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all ${
                  isCrawling 
                    ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700' 
                    : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-900/20'
                }`}
              >
                {isCrawling ? 'Processing...' : <><Play className="w-4 h-4 fill-current" /> Start Extraction</>}
              </button>
            </div>
          </div>

          {/* Logs Console */}
          <div className="flex-1 bg-black rounded-xl border border-slate-800 overflow-hidden flex flex-col font-mono text-xs shadow-inner">
            <div className="bg-slate-900 px-4 py-2 text-slate-400 border-b border-slate-800 flex justify-between">
              <span>Execution Logs</span>
              {isCrawling && <span className="text-emerald-500 animate-pulse">● Live</span>}
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {logs.length === 0 && <span className="text-slate-700 italic">Ready to crawl...</span>}
              {logs.map((log, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-slate-600">[{new Date().toLocaleTimeString()}]</span>
                  <span className={`
                    ${log.type === 'error' ? 'text-red-400' : ''}
                    ${log.type === 'success' ? 'text-emerald-400' : ''}
                    ${log.type === 'info' ? 'text-blue-300' : ''}
                    ${log.type === 'warning' ? 'text-yellow-400' : ''}
                  `}>
                    {log.type === 'success' ? '✔' : '➜'} {log.message}
                  </span>
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>

        {/* Right Panel: File Explorer & Preview */}
        <div className="lg:col-span-8 bg-slate-900 rounded-xl border border-slate-800 flex overflow-hidden shadow-xl">
          {/* File Tree */}
          <div className="w-1/3 border-r border-slate-800 bg-slate-900/50 flex flex-col">
            <div className="p-4 border-b border-slate-800 font-semibold text-slate-300 flex items-center gap-2">
              <FolderOpen className="w-4 h-4 text-emerald-500" /> Output Files
            </div>
            <div className="overflow-y-auto flex-1 p-2">
              {files.length === 0 && <div className="text-center text-slate-600 mt-10 text-sm">No files yet</div>}
              {files.map((group, idx) => (
                <div key={idx} className="mb-4">
                  <h3 className="text-[10px] font-bold text-slate-500 uppercase px-3 mb-2 tracking-wider">{group.domain}</h3>
                  <div className="space-y-1">
                    {group.files.map((file, fIdx) => (
                      <button 
                        key={fIdx}
                        onClick={() => fetchFileContent(group.domain, file)}
                        className={`w-full text-left px-3 py-2 text-sm rounded transition-colors flex items-center gap-2 truncate ${
                          selectedFile?.name === file ? 'bg-emerald-500/10 text-emerald-400' : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                        }`}
                      >
                        <FileText className="w-3 h-3 opacity-70" /> 
                        <span className="truncate">{file}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Markdown Preview */}
          <div className="flex-1 flex flex-col bg-slate-950">
            <div className="p-4 border-b border-slate-800 bg-slate-900 flex justify-between items-center">
              <span className="font-mono text-sm text-slate-300">
                {selectedFile ? selectedFile.name : "Select a file to preview"}
              </span>
            </div>
            <div className="flex-1 overflow-y-auto p-8">
              {selectedFile ? (
                <article className="prose prose-invert prose-emerald max-w-none prose-img:rounded-lg prose-headings:text-slate-100 prose-a:text-emerald-400">
                  <ReactMarkdown>{selectedFile.content}</ReactMarkdown>
                </article>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-slate-700 gap-4">
                  <FileText className="w-16 h-16 opacity-20" />
                  <p>Content preview will appear here</p>
                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default App;