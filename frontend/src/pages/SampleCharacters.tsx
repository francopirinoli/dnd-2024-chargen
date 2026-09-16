import { useNavigate, Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { ChevronLeft } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useCharacterStore } from "@/store/characterStore";
import { SAMPLE_CHARACTERS, type SampleCharacter } from "@/data/sampleCharacters";

function CharacterCard({
  char,
  onLoad,
}: {
  char: SampleCharacter;
  onLoad: (char: SampleCharacter) => void;
}) {
  const imgSrc = `/images/classes/${char.classKey}-card.png`;

  return (
    <article
      role="button"
      tabIndex={0}
      onClick={() => onLoad(char)}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onLoad(char)}
      className="rounded-lg border border-border bg-card flex flex-col overflow-hidden group hover:border-primary/50 cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-primary/50"
    >
      <div className="relative aspect-[3/4] bg-muted overflow-hidden">
        <img
          src={imgSrc}
          alt={`${char.characterClass} illustration`}
          className="w-full h-full object-cover object-top transition-transform duration-500 group-hover:scale-105"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-card via-transparent to-transparent" />
        <span className="absolute bottom-3 left-3 rounded-full border border-border bg-card/80 backdrop-blur-sm px-2.5 py-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">
          Level 3
        </span>
      </div>

      <div className="p-4 flex flex-col gap-1.5 flex-1">
        <h2 className="font-display text-lg text-foreground leading-tight">
          {char.name}
        </h2>
        <p className="text-xs font-semibold text-primary/80 uppercase tracking-wider">
          {char.species} {char.characterClass}
        </p>
        <p className="text-xs text-muted-foreground">
          {char.subclass}
        </p>
        <p className="text-sm text-muted-foreground italic mt-1 leading-relaxed">
          "{char.flavor}"
        </p>
        <p className="mt-auto pt-3 text-xs font-semibold text-primary group-hover:underline">
          View Sheet →
        </p>
      </div>
    </article>
  );
}

export function SampleCharacters() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  function handleLoad(char: SampleCharacter) {
    useCharacterStore.setState({
      choicesMade: char.choices,
      currentStepId: null,
    });
    queryClient.removeQueries({ queryKey: ["character"] });
    queryClient.removeQueries({ queryKey: ["wizard"] });
    navigate("/sheet");
  }

  return (
    <main className="min-h-dvh bg-background text-foreground font-sans">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container max-w-7xl flex items-center justify-between h-14 px-6">
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            Back to Home
          </Link>

          <div className="absolute left-1/2 -translate-x-1/2">
            <h1 className="font-display text-lg text-primary tracking-wide hidden sm:block">
              Sample Characters
            </h1>
          </div>

          <ThemeToggle />
        </div>
      </header>

      {/* Hero blurb */}
      <section className="border-b border-border bg-card/30 px-6 py-10 text-center">
        <h2 className="font-display text-3xl md:text-4xl text-primary tracking-wide mb-3">
          Pre-Built Characters
        </h2>
        <p className="text-muted-foreground max-w-2xl mx-auto leading-relaxed">
          Twelve pre-configured Level 3 characters covering each core class.
          Select any character to immediately view and interact with their complete character sheet.
        </p>
      </section>

      {/* Character grid */}
      <div className="container max-w-7xl px-6 py-12">
        <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-4">
          {SAMPLE_CHARACTERS.map((char) => (
            <CharacterCard key={char.id} char={char} onLoad={handleLoad} />
          ))}
        </div>
      </div>
    </main>
  );
}
