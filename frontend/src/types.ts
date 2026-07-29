export interface Post {
  id: string;
  date: string;
  caption: string;
  media: string[];
  comments: string[];
  url?: string;
  thumbnail?: string;
}
