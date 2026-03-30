package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
	"regexp"
	"sort"
	"strings"
)

type Book struct {
	ID                int      `json:"id"`
	Title             string   `json:"title"`
	Author            string   `json:"author"`
	Genre             string   `json:"genre"`
	Summary           string   `json:"summary"`
	Description       string   `json:"description"`
	AvailableQuantity int      `json:"available_quantity"`
	Quantity          int      `json:"quantity"`
	PublishedYear     int      `json:"published_year"`
	Subjects          []string `json:"subjects"`
}

type Intent struct {
	SearchQuery  string   `json:"search_query"`
	CourseFocus  string   `json:"course_focus"`
	Mood         string   `json:"mood"`
	ReadingLevel string   `json:"reading_level"`
	Explanation  string   `json:"explanation"`
	Tags         []string `json:"tags"`
}

type RankRequest struct {
	Query  string `json:"query"`
	Intent Intent `json:"intent"`
	Books  []Book `json:"books"`
}

type RankedBook struct {
	ID     int     `json:"id"`
	Score  float64 `json:"score"`
	Reason string  `json:"reason"`
}

type RankResponse struct {
	Ranked []RankedBook `json:"ranked"`
}

var tokenRe = regexp.MustCompile(`[a-z0-9]+`)

func tokenize(text string) map[string]int {
	out := map[string]int{}
	for _, token := range tokenRe.FindAllString(strings.ToLower(text), -1) {
		out[token]++
	}
	return out
}

func overlap(a, b map[string]int) float64 {
	total := 0.0
	for token, countA := range a {
		if countB, ok := b[token]; ok {
			if countA < countB {
				total += float64(countA)
			} else {
				total += float64(countB)
			}
		}
	}
	return total
}

func scoreBook(queryTokens map[string]int, intent Intent, book Book) (float64, string) {
	document := strings.Join([]string{
		book.Title,
		book.Author,
		book.Genre,
		book.Summary,
		book.Description,
		strings.Join(book.Subjects, " "),
	}, " ")
	docTokens := tokenize(document)
	intentTokens := tokenize(strings.Join(append(intent.Tags, intent.CourseFocus, intent.Mood, intent.ReadingLevel), " "))

	lexical := overlap(queryTokens, docTokens) * 1.6
	intentScore := overlap(intentTokens, docTokens) * 1.2
	availability := 0.25
	if book.AvailableQuantity > 0 {
		availability = 1.6
	}
	freshness := 0.0
	if book.PublishedYear >= 2012 {
		freshness = 0.25
	}
	score := lexical + intentScore + availability + freshness

	reasonParts := []string{}
	if lexical > 0 {
		reasonParts = append(reasonParts, "strong topic match")
	}
	if intentScore > 0 {
		reasonParts = append(reasonParts, "fits the inferred class need")
	}
	if book.AvailableQuantity > 0 {
		reasonParts = append(reasonParts, "available now")
	}
	if len(reasonParts) == 0 {
		reasonParts = append(reasonParts, "broad catalog fit")
	}
	return score, strings.Join(reasonParts, " · ")
}

func rankHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST required", http.StatusMethodNotAllowed)
		return
	}

	var req RankRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid JSON", http.StatusBadRequest)
		return
	}

	queryTokens := tokenize(req.Query)
	if req.Intent.SearchQuery != "" {
		for token, count := range tokenize(req.Intent.SearchQuery) {
			queryTokens[token] += count
		}
	}

	ranked := make([]RankedBook, 0, len(req.Books))
	for _, book := range req.Books {
		score, reason := scoreBook(queryTokens, req.Intent, book)
		ranked = append(ranked, RankedBook{
			ID:     book.ID,
			Score:  score,
			Reason: reason,
		})
	}

	sort.Slice(ranked, func(i, j int) bool {
		return ranked[i].Score > ranked[j].Score
	})

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(RankResponse{Ranked: ranked})
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
}

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/rank", rankHandler)
	mux.HandleFunc("/healthz", healthHandler)

	addr := os.Getenv("GO_RANKER_ADDR")
	if addr == "" {
		addr = ":8088"
	}

	log.Printf("go-ranker listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, mux))
}
