---
type: tool
---

# Fast Google Drive

Lists a class `content` folder or recent Drive files. `download --fileId ID --class CODE --apply` retains a PDF in `attachments/`.

JSON in, JSON out. The default command is `run`. Items the runner will not guess are listed under `needs_llm`.

```powershell
.\tools\fast-google-drive\fast-google-drive.ps1 --class "MATH 245"
.\tools\fast-google-drive\fast-google-drive.ps1 download --fileId FILE_ID --class "MATH 245" --apply
```
