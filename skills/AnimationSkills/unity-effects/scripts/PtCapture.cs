using System.Collections; using System.Collections.Generic; using System.IO; using System.Text; using UnityEngine;
namespace Annie {
public class PtCapture : MonoBehaviour {
  public static PtCapture I; public string outDir; public int fps=30; public int count; public bool running; public int max=100000;
  StringBuilder audio=new StringBuilder(); StringBuilder marks=new StringBuilder(); HashSet<int> seen=new HashSet<int>();
  StringBuilder cues=new StringBuilder(); bool hooked;
  void Hook(){ if(hooked) return; hooked=true; GuildMastersDescent.Game.GameAudio.Requested+=e=>{ cues.Append("{\"frame\":"+count+",\"cue\":\""+(e.Cue.HasValue?e.Cue.ToString():"Music "+e.Music)+"\",\"bucket\":\""+e.Bucket+"\",\"clip\":\""+e.Clip+"\"},\n"); }; }
  public static PtCapture Get(){ if(I==null){var g=new GameObject("PtCapture"); DontDestroyOnLoad(g); I=g.AddComponent<PtCapture>();} return I; }
  public static string Begin(string dir,int fps,int max){ var c=Get(); Directory.CreateDirectory(dir+"/frames"); c.outDir=dir; c.fps=fps; c.count=0; c.max=max; c.audio.Length=0; c.marks.Length=0; c.seen.Clear(); Application.runInBackground=true; Time.captureFramerate=fps; c.Hook(); c.cues.Length=0; c.running=true; c.StartCoroutine(c.Run()); return "begin "+dir+" "+Screen.width+"x"+Screen.height; }
  public static string Mark(string s){ var c=Get(); c.marks.Append("{\"frame\":"+c.count+",\"mark\":\""+s.Replace("\"","'")+"\"},\n"); return "mark "+c.count; }
  public struct Act{public int frame; public string kind,arg;}
  public List<Act> sched=new List<Act>();
  public static string At(int frame,string kind,string arg){ Get().sched.Add(new Act{frame=frame,kind=kind,arg=arg}); return "sched"; }
  public static string List(){ var sb=new StringBuilder(); foreach(var b in FindObjectsByType<UnityEngine.UI.Button>(FindObjectsInactive.Exclude)){ var tx=b.GetComponentInChildren<UnityEngine.UI.Text>(); sb.Append(b.name+"|"+(tx!=null?tx.text:"")+"|"+b.interactable+"|"+b.transform.parent.name+"\n"); } return sb.ToString(); }
  public static string Click(string name){ foreach(var b in FindObjectsByType<UnityEngine.UI.Button>(FindObjectsInactive.Exclude)){ if(b.name==name&&b.interactable){ b.onClick.Invoke(); return "clicked "+name; } } return "NOT FOUND "+name; }
  public static string End(){ var c=Get(); c.running=false; return "end "+c.count; }
  IEnumerator Run(){
    while(running && count<max){
      for(int i=sched.Count-1;i>=0;i--){ if(sched[i].frame<=count){ var a0=sched[i]; sched.RemoveAt(i); if(a0.kind=="click") marks.Append("{\"frame\":"+count+",\"mark\":\"click "+a0.arg+": "+Click(a0.arg)+"\"},\n"); else if(a0.kind=="mark") Mark(a0.arg); } }
      yield return new WaitForEndOfFrame();
      var t=ScreenCapture.CaptureScreenshotAsTexture();
      File.WriteAllBytes(outDir+"/frames/f"+count.ToString("0000")+".png",t.EncodeToPNG()); int w=t.width,h=t.height; Destroy(t);
      foreach(var a in FindObjectsByType<AudioSource>(FindObjectsInactive.Exclude)){ if(a.isPlaying&&a.clip!=null){ int id=a.GetHashCode()*31+a.clip.GetHashCode(); if(seen.Add(id)){ audio.Append("{\"frame\":"+count+",\"clip\":\""+a.clip.name+"\",\"src\":\""+a.name+"\",\"vol\":"+a.volume+"},\n"); } } else if(!a.isPlaying&&a.clip!=null){ seen.Remove(a.GetHashCode()*31+a.clip.GetHashCode()); } }
      count++; if(count==1) File.WriteAllText(outDir+"/size.txt",w+"x"+h);
    }
    Time.captureFramerate=0; running=false;
    File.WriteAllText(outDir+"/capture.json","{\"fps\":"+fps+",\"frames\":"+count+",\"size\":\""+Screen.width+"x"+Screen.height+"\",\"timeScale\":"+Time.timeScale+",\"scene\":\""+UnityEngine.SceneManagement.SceneManager.GetActiveScene().name+"\"}");
    File.WriteAllText(outDir+"/audio_plays.json","["+audio+"]"); File.WriteAllText(outDir+"/cues.json","["+cues+"]"); File.WriteAllText(outDir+"/marks.json","["+marks+"]");
  }
}}
